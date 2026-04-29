"""
Custom exceptions for the Dota 2 MMR backend.
Route handlers map these to HTTP status codes; keep raise sites in service layer only.
"""


class DotaBackendError(Exception):
    """Base class for all backend errors."""


class StratzAPIError(DotaBackendError):
    """Stratz GraphQL API returned an error, timed out, or was unreachable (→ 502)."""


class PlayerNotFoundError(DotaBackendError):
    """Steam ID returned no Stratz data (→ 404)."""


class MatchNotFoundError(DotaBackendError):
    """Match not found for this player via Stratz (→ 404)."""
