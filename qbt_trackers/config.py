"""Configuration loading: config.toml (native via tomllib).

`load_settings` never raises on a missing/partial file - it falls back to sane
defaults (a local WebUI on :8080). Validation is separate and explicit:
`Settings.require()` refuses to run against an unreachable-looking config with an
actionable message, mirroring the CLI's own error style.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = _ROOT / "config.toml"


@dataclass(frozen=True)
class QbitConfig:
    """How to reach the qBittorrent Web API.

    Username/password may be empty: qBittorrent can be set to bypass auth for
    local connections, in which case only host/port matter.
    """

    host: str = "localhost"
    port: int = 8080
    username: str = ""
    password: str = ""
    https: bool = False
    verify_cert: bool = True

    @property
    def base_url(self) -> str:
        scheme = "https" if self.https else "http"
        return f"{scheme}://{self.host}:{self.port}"

    @property
    def is_configured(self) -> bool:
        return bool(self.host and self.port)


@dataclass(frozen=True)
class Settings:
    qbit: QbitConfig = field(default_factory=QbitConfig)

    def require(self) -> QbitConfig:
        """Refuse to run without a host/port to connect to."""
        if not self.qbit.is_configured:
            raise SystemExit(
                "qBittorrent connection is not configured.\n"
                "Add a [qbittorrent] section with host/port (and WebUI username/password) "
                "to config.toml - see config.example.toml."
            )
        return self.qbit


def load_settings(config_path: Path | None = None) -> Settings:
    """Read config.toml if present; otherwise return defaults (local WebUI)."""
    path = config_path or DEFAULT_CONFIG
    data: dict = {}
    if path.exists():
        with open(path, "rb") as f:
            data = tomllib.load(f)

    qb = data.get("qbittorrent", {})
    return Settings(
        qbit=QbitConfig(
            host=str(qb.get("host") or "localhost"),
            port=int(qb.get("port") or 8080),
            username=str(qb.get("username") or ""),
            password=str(qb.get("password") or ""),
            https=bool(qb.get("https", False)),
            verify_cert=bool(qb.get("verify_cert", True)),
        )
    )
