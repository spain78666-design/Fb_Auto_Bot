"""
Automation package marker and exports
"""
from .browser_bot import (
    FacebookMarketplaceBot,
    parse_cookie_payload,
    parse_proxy_payload,
    MarketplaceBotError,
    InvalidSessionError,
    CheckpointDetectedError,
    ProxyConnectionError,
    NavigationTimeoutError,
    ListingSubmissionError
)
from .session_manager import (
    SessionManager,
    SessionCookieParser,
    get_session_manager
)

__all__ = [
    "FacebookMarketplaceBot",
    "parse_cookie_payload",
    "parse_proxy_payload",
    "MarketplaceBotError",
    "InvalidSessionError",
    "CheckpointDetectedError",
    "ProxyConnectionError",
    "NavigationTimeoutError",
    "ListingSubmissionError",
    "SessionManager",
    "SessionCookieParser",
    "get_session_manager"
]
