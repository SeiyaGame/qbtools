"""Edit qBittorrent tracker URLs in bulk, filtered by category / tag / state.

Talks to a running qBittorrent over its Web API (`qbittorrent-api`) rather than
poking `.fastresume` files on disk: the API is live (no need to stop the client),
and it already knows how to filter by category, tag and state - exactly the axes
this tool selects torrents on.

Everything is dry-run by default: a command prints the plan it *would* apply and
touches nothing until `--run` is passed.
"""

__version__ = "0.1.0"
