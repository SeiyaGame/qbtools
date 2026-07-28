"""Thin wrapper over `qbittorrent-api`, mapping raw payloads into `models.py`.

The rest of the tool only ever sees `TorrentInfo`/`Tracker`, never a qBittorrent
AttrDict. All the library's exception types are funnelled into our own typed
errors here, so callers catch `TrackerToolError` and nothing leaks the dependency.
"""

from __future__ import annotations

import qbittorrentapi

from .config import QbitConfig
from .errors import ApiError, AuthError, QbitConnectionError
from .models import TorrentFilter, TorrentInfo, Tracker, TrackerStatus


class _ApiProxy:
    """Wraps the raw qBittorrent client so every call *it* makes turns a library
    failure into an `ApiError` - one boundary instead of a decorator on every method.

    Methods reach the library only through here (`self.api`), so they read as plain
    calls; the original exception is kept as the `ApiError.__cause__` for the rare
    caller that needs to tell one apart (see `set_category`).
    """

    def __init__(self, api: qbittorrentapi.Client):
        self._api = api

    def __getattr__(self, name: str):
        attr = getattr(self._api, name)
        if not callable(attr):
            return attr

        def call(*args, **kwargs):
            try:
                return attr(*args, **kwargs)
            except qbittorrentapi.APIError as exc:  # the library's own base - our code bugs still surface
                raise ApiError(f"{name}: {exc}") from exc

        return call


class QbitClient:
    """A connected qBittorrent session. Build it, `connect()`, then query/mutate."""

    def __init__(self, config: QbitConfig):
        self.config = config
        self._api = None
        self._proxy: _ApiProxy | None = None

    def connect(self) -> QbitClient:
        """Log in. Raises `QbitConnectionError` / `AuthError` on failure."""
        api = qbittorrentapi.Client(
            host=self.config.base_url,
            username=self.config.username or None,
            password=self.config.password or None,
            VERIFY_WEBUI_CERTIFICATE=self.config.verify_cert,
            REQUESTS_ARGS={"timeout": 15},
        )
        try:
            api.auth_log_in()
        except qbittorrentapi.LoginFailed as exc:
            raise AuthError(f"Login refused by qBittorrent: {exc}") from exc
        except qbittorrentapi.Forbidden403Error as exc:
            raise AuthError("qBittorrent returned 403 (IP banned after failed logins?).") from exc
        except qbittorrentapi.APIConnectionError as exc:
            raise QbitConnectionError(f"Cannot reach qBittorrent at {self.config.base_url}: {exc}") from exc
        self._api = api
        self._proxy = _ApiProxy(api)
        return self

    @property
    def api(self) -> _ApiProxy:
        """The library client, wrapped so its failures surface as `ApiError`."""
        if self._proxy is None:
            raise QbitConnectionError("Not connected - call connect() first.")
        return self._proxy

    def versions(self) -> tuple[str, str]:
        """(application version, Web API version), for the `ping` command."""
        return str(self.api.app_version()), str(self.api.app_web_api_version())

    def categories(self) -> list[str]:
        return sorted(self.api.torrents_categories().keys())

    def tags(self) -> list[str]:
        return sorted(self.api.torrents_tags())

    def torrents(self, filter: TorrentFilter) -> list[TorrentInfo]:
        """Filtered torrents, each with its trackers resolved.

        Server-side axes go through `torrents_info`; the trackers of each hit are
        fetched (one call per torrent - the API has no bulk tracker read) and the
        client-side `filter.matches` refinement is applied last.
        """
        result: list[TorrentInfo] = []
        for t in self.api.torrents_info(**filter.api_kwargs()):
            info = TorrentInfo(
                hash=t.hash,
                name=t.name,
                category=t.category or "",
                tags=tuple(tag.strip() for tag in (t.tags or "").split(",") if tag.strip()),
                state=str(t.state),
                save_path=t.save_path,
                trackers=self._trackers(t.hash),
            )
            if filter.matches(info):
                result.append(info)
        return result

    def _trackers(self, torrent_hash: str) -> tuple[Tracker, ...]:
        return tuple(
            Tracker(
                url=r.get("url", ""),
                status=TrackerStatus.from_code(r.get("status")),
                tier=int(r.get("tier") or 0),
                message=r.get("msg", ""),
                num_peers=int(r.get("num_peers", -1)),
            )
            for r in self.api.torrents_trackers(torrent_hash=torrent_hash)
        )

    def edit_tracker(self, torrent_hash: str, old_url: str, new_url: str) -> None:
        self.api.torrents_edit_tracker(torrent_hash=torrent_hash, original_url=old_url, new_url=new_url)

    def add_tracker(self, torrent_hash: str, url: str) -> None:
        self.api.torrents_add_trackers(torrent_hash=torrent_hash, urls=url)

    def remove_tracker(self, torrent_hash: str, url: str) -> None:
        self.api.torrents_remove_trackers(torrent_hash=torrent_hash, urls=url)

    def add_tags(self, torrent_hash: str, tag: str) -> None:
        self.api.torrents_add_tags(tags=tag, torrent_hashes=torrent_hash)

    def remove_tags(self, torrent_hash: str, tag: str) -> None:
        self.api.torrents_remove_tags(tags=tag, torrent_hashes=torrent_hash)

    def set_category(self, torrent_hash: str, category: str) -> None:
        """Set the category, creating it first if qBittorrent doesn't know it yet.

        Setting an unknown category is an error, so create it when missing rather
        than react to the failure. The empty category (uncategorised) always exists.
        """
        if category and category not in self.api.torrents_categories():
            self.api.torrents_create_category(name=category)
        self.api.torrents_set_category(category=category, torrent_hashes=torrent_hash)

    def set_location(self, torrent_hash: str, location: str) -> None:
        self.api.torrents_set_location(location=location, torrent_hashes=torrent_hash)

    def rename(self, torrent_hash: str, name: str) -> None:
        self.api.torrents_rename(torrent_hash=torrent_hash, new_torrent_name=name)
