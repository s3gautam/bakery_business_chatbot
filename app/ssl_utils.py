"""Local-dev-only workaround for corporate SSL/TLS interception.

Never enabled by default. See CLAUDE.md > "Local Dev Environment:
Corporate SSL Interception" for the policy this implements.
"""

import structlog
import httpx

from app.config import Settings

logger = structlog.get_logger(__name__)


def build_httpx_verify(settings: Settings) -> str | bool:
    """Resolve the `verify` argument for an httpx client.

    Preference order:
    1. A corporate CA bundle path, if configured.
    2. `DEV_DISABLE_SSL_VERIFY=true`, but only outside production.
    3. Default (verify=True).
    """
    if settings.requests_ca_bundle:
        return settings.requests_ca_bundle

    if settings.dev_disable_ssl_verify:
        if settings.is_production:
            raise RuntimeError(
                "DEV_DISABLE_SSL_VERIFY must never be set in production."
            )
        logger.warning(
            "ssl_verification_disabled",
            reason="DEV_DISABLE_SSL_VERIFY=true on a non-production environment",
        )
        return False

    return True


def build_httpx_client(settings: Settings, **kwargs) -> httpx.Client:
    return httpx.Client(verify=build_httpx_verify(settings), **kwargs)


def build_async_httpx_client(settings: Settings, **kwargs) -> httpx.AsyncClient:
    return httpx.AsyncClient(verify=build_httpx_verify(settings), **kwargs)
