"""Typed errors shared across the tool.

Two audiences: config/connection problems the *user* must fix raise `SystemExit`
with an actionable message (handled at the CLI edge). Everything below is for
control flow inside the pipeline, so a failed API call is distinguishable from a
misconfiguration.
"""

from __future__ import annotations


class TrackerToolError(Exception):
    """Base class for every error raised by this package."""


class QbitConnectionError(TrackerToolError):
    """The qBittorrent Web API could not be reached (host down, wrong port)."""


class AuthError(TrackerToolError):
    """Login was refused (bad WebUI username/password, or IP banned)."""


class ApiError(TrackerToolError):
    """qBittorrent accepted the request but rejected or failed the operation."""
