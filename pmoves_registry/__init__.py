"""
PMOVES.AI Service Registry Integration Template

Service discovery using the PMOVES service registry with fallback chain:
1. Environment variables (static overrides)
2. Supabase service catalog (dynamic, runtime)
3. NATS service announcements (real-time, cached)
4. Docker DNS (development fallback)

Usage:
    from pmoves_registry import get_service_url, ServiceInfo

    # Simple URL resolution
    url = await get_service_url('hirag-v2')

    # Get full service info
    info = await get_service_info('hirag-v2')
    print(f'{info.name}: {info.health_check_url}')
"""

import asyncio
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ServiceTier(str, Enum):
    """PMOVES service tiers."""
    DATA = 'data'
    API = 'api'
    LLM = 'llm'
    MEDIA = 'media'
    AGENT = 'agent'
    WORKER = 'worker'
    APP = 'app'
    UI = 'ui'


@dataclass(frozen=True)
class ServiceInfo:
    """
    Immutable service metadata from the service catalog.

    Attributes:
        slug: Unique service identifier (e.g., 'hirag-v2', 'agent-zero')
        name: Human-readable service name
        description: Service description
        health_check_url: Full URL to health check endpoint
        base_url: Base URL of the service
        default_port: Default container port
        tier: Service tier classification
        metadata: Extended metadata as JSON
    """

    slug: str
    name: str
    description: str
    health_check_url: str
    default_port: int | None
    tier: ServiceTier
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def base_url(self) -> str:
        """Extract base URL from health_check_url."""
        url = self.health_check_url
        for suffix in ('/healthz', '/health', '/metrics', '/ping'):
            if url.endswith(suffix):
                url = url[: -len(suffix)]
                break
        return url.rstrip('/')


class ServiceNotFoundError(Exception):
    """Raised when a service cannot be found."""

    def __init__(self, slug: str, message: str | None = None):
        self.slug = slug
        super().__init__(message or f"Service '{slug}' not found in service catalog")


def _get_env_url(slug: str) -> str | None:
    """
    Check for environment variable override.

    Environment variables are checked in the following order:
    1. slug with dashes replaced by underscores (e.g., 'hirag-v2' -> HIRAG_V2_URL)
    2. slug with dashes removed (e.g., 'hirag-v2' -> HIRAGV2_URL)
    3. original uppercase slug with dashes preserved (e.g., 'hirag-v2' -> HIRAG-V2_URL)

    Args:
        slug: Service slug (e.g., 'hirag-v2')

    Returns:
        URL from environment or None
    """
    env_var_patterns = [
        slug.upper().replace('-', '_') + '_URL',  # HIRAG_V2_URL
        slug.upper().replace('-', '') + '_URL',  # HIRAGV2_URL
        slug.upper() + '_URL',  # HIRAG-V2_URL
    ]

    for pattern in env_var_patterns:
        if url := os.getenv(pattern):
            return url

    return None


def _fallback_dns_url(slug: str, default_port: int) -> str:
    """
    Generate fallback URL using Docker DNS.

    Args:
        slug: Service slug (used as DNS name)
        default_port: Port to use if service has no default

    Returns:
        Fallback service URL
    """
    return f'http://{slug}:{default_port}'


async def get_service_info(
    slug: str,
    *,
    default_port: int = 80,
) -> ServiceInfo:
    """
    Get complete service information using fallback chain.

    Resolution order:
        1. Environment variable override
        2. DNS-based fallback (always succeeds)

    Args:
        slug: Service slug to resolve
        default_port: Port for fallback URL construction

    Returns:
        ServiceInfo with service metadata
    """
    # 1. Check environment variable override
    if env_url := _get_env_url(slug):
        return ServiceInfo(
            slug=slug,
            name=f'{slug} (from env)',
            description='Service URL from environment variable',
            health_check_url=env_url.rstrip('/') + '/healthz',
            default_port=default_port,
            tier=ServiceTier.API,  # Default tier
        )

    # 2. Fallback to DNS-based URL
    fallback_url = _fallback_dns_url(slug, default_port)
    return ServiceInfo(
        slug=slug,
        name=f'{slug} (fallback)',
        description='Service resolved via Docker DNS fallback',
        health_check_url=fallback_url + '/healthz',
        default_port=default_port,
        tier=ServiceTier.API,
    )


async def get_service_url(
    slug: str,
    *,
    default_port: int = 80,
    use_base_url: bool = True,
) -> str:
    """
    Resolve service URL with fallback chain.

    Args:
        slug: Service slug to resolve
        default_port: Port for fallback URL construction
        use_base_url: Return base URL instead of health_check_url

    Returns:
        Resolved service URL

    Example:
        >>> await get_service_url('hirag-v2')
        'http://hi-rag-gateway-v2:8086'
    """
    info = await get_service_info(slug, default_port=default_port)
    return info.base_url if use_base_url else info.health_check_url


async def check_service_health(
    slug: str,
    *,
    default_port: int = 80,
    timeout: float = 5.0,
) -> bool:
    """
    Check if a service is healthy by calling its health endpoint.

    Args:
        slug: Service slug to check
        default_port: Port for fallback URL construction
        timeout: HTTP request timeout in seconds

    Returns:
        True if service is healthy, False otherwise
    """
    import httpx

    info = await get_service_info(slug, default_port=default_port)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(info.health_check_url)
            return response.status_code == 200
    except Exception:
        return False


# Common service URLs for quick reference
class CommonServices:
    """Common PMOVES service URLs for quick reference."""

    # Agent Coordination
    AGENT_ZERO = 'http://agent-zero:8080'
    ARCHON = 'http://archon:8091'
    MESH_AGENT = 'mesh-agent'  # No HTTP interface

    # LLM Gateway
    TENSORZERO = 'http://tensorzero-gateway:3030'
    TENSORZERO_UI = 'http://tensorzero-ui:4000'

    # Retrieval
    HIRAG_V2 = 'http://hi-rag-gateway-v2:8086'
    HIRAG_V1 = 'http://hi-rag-gateway:8089'

    # Data Services
    QDRANT = 'http://qdrant:6333'
    NEO4J = 'http://neo4j:7474'
    MEILISEARCH = 'http://meilisearch:7700'
    MINIO = 'http://minio:9000'

    # NATS
    NATS = 'nats://nats:4222'

    @classmethod
    def get(cls, service: str) -> str | None:
        """Get a common service URL by name."""
        return getattr(cls, service.upper(), None)


if __name__ == '__main__':
    # Example usage
    async def main():
        # Get service URL
        url = await get_service_url('hirag-v2', default_port=8086)
        print(f'Hi-RAG URL: {url}')

        # Check service health
        healthy = await check_service_health('hirag-v2', default_port=8086)
        print(f'Hi-RAG Healthy: {healthy}')

        # Get service info
        info = await get_service_info('agent-zero', default_port=8080)
        print(f'Service: {info.name}')
        print(f'Base URL: {info.base_url}')
        print(f'Health Check: {info.health_check_url}')

    asyncio.run(main())
