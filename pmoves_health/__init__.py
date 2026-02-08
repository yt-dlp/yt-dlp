"""
PMOVES.AI Health Endpoint Template

Standard health check endpoint for all PMOVES services.
Follows PMOVES.AI conventions for service health monitoring.

Usage:
    from pmoves_health import create_health_app
    app = create_health_app()

    # Or add to existing FastAPI app
    from pmoves_health import health_check_router
    app.include_router(health_check_router)
"""

from collections.abc import Callable
from datetime import datetime, timezone
from functools import wraps
from typing import TYPE_CHECKING, Any
import os
import asyncio

if TYPE_CHECKING:
    from fastapi import FastAPI

try:
    from fastapi import APIRouter
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False


# Health check configuration
HEALTH_CHECK_PATH = '/healthz'
HEALTH_CHECK_TIMEOUT = 5.0


class HealthStatus:
    """Health status constants."""
    HEALTHY = 'healthy'
    DEGRADED = 'degraded'
    UNHEALTHY = 'unhealthy'


class DependencyCheck:
    """Base class for dependency health checks."""

    def __init__(self, name: str, required: bool = True):
        self.name = name
        self.required = required

    async def check(self) -> bool:
        """Check if dependency is healthy. Override in subclass."""
        raise NotImplementedError

    def status_key(self) -> str:
        """Return the status key for this check."""
        return f'{self.name.lower().replace(" ", "_")}_connected'


class DatabaseCheck(DependencyCheck):
    """Health check for database connections."""

    def __init__(self, connect_fn: Callable, **kwargs):
        super().__init__('database', kwargs.get('required', True))
        self.connect_fn = connect_fn

    async def check(self) -> bool:
        try:
            return await asyncio.to_thread(self.connect_fn)
        except Exception:
            return False


class HTTPCheck(DependencyCheck):
    """Health check for HTTP endpoints."""

    def __init__(self, url: str, **kwargs):
        name = kwargs.get('name', 'service')
        super().__init__(name, kwargs.get('required', True))
        self.url = url

    async def check(self) -> bool:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(self.url)
                return response.status_code == 200
        except Exception:
            return False


class NATSCheck(DependencyCheck):
    """Health check for NATS connection."""

    def __init__(self, nats_url: str, **kwargs):
        super().__init__('nats', kwargs.get('required', True))
        self.nats_url = nats_url

    async def check(self) -> bool:
        try:
            # Use the module-level nats.connect() helper, not Client.connect()
            import nats
            nc = await nats.connect(self.nats_url, connect_timeout=2)
            await nc.close()
            return True
        except Exception:
            return False


class HealthChecker:
    """Health checker with multiple dependency checks."""

    def __init__(self, service_name: str | None = None):
        self.service_name = service_name or os.getenv('SERVICE_NAME', 'unknown')
        self.checks: list[DependencyCheck] = []
        self.custom_checks: dict[str, Callable] = {}

    def add_check(self, check: DependencyCheck) -> None:
        """Add a dependency check with deduplication guard."""
        if check not in self.checks:
            self.checks.append(check)

    def add_custom_check(self, name: str, check_fn: Callable) -> None:
        """Add a custom health check function."""
        self.custom_checks[name] = check_fn

    def database(self, connect_fn: Callable) -> None:
        """Add a database health check."""
        self.add_check(DatabaseCheck(connect_fn))

    def http(self, url: str, name: str = 'service') -> None:
        """Add an HTTP endpoint health check."""
        self.add_check(HTTPCheck(url, name=name))

    def nats(self, nats_url: str) -> None:
        """Add a NATS health check."""
        self.add_check(NATSCheck(nats_url))

    async def check_all(self) -> dict[str, Any]:
        """Run all health checks and return status."""
        results = {
            'status': HealthStatus.HEALTHY,
            'service': self.service_name,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }

        all_healthy = True
        some_degraded = False

        # Run dependency checks
        for check in self.checks:
            try:
                is_healthy = await check.check()
                results[check.status_key()] = is_healthy

                if not is_healthy:
                    if check.required:
                        all_healthy = False
                    else:
                        some_degraded = True
            except Exception:
                results[check.status_key()] = False
                if check.required:
                    all_healthy = False
                else:
                    some_degraded = True

        # Run custom checks
        for name, check_fn in self.custom_checks.items():
            try:
                result = await check_fn() if asyncio.iscoroutinefunction(check_fn) else check_fn()
                results[name] = bool(result)
                if not result:
                    all_healthy = False
            except Exception:
                results[name] = False
                all_healthy = False

        # Determine overall status
        if not all_healthy:
            results['status'] = HealthStatus.UNHEALTHY
        elif some_degraded:
            results['status'] = HealthStatus.DEGRADED

        return results


# Global health checker instance
_health_checker = HealthChecker()


def health_check(checks: list[DependencyCheck] | None = None):
    """
    Decorator to add health checks to a function.

    Checks are registered once at decoration time, not on each call.
    This prevents duplicate registrations when the decorated function is called repeatedly.
    """
    # Register checks immediately when decorator is applied (not on each call)
    if checks:
        for check in checks:
            _health_checker.add_check(check)

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def add_database_check(connect_fn: Callable) -> None:
    """Add a database health check."""
    _health_checker.database(connect_fn)


def add_http_check(url: str, name: str = 'service') -> None:
    """Add an HTTP endpoint health check."""
    _health_checker.http(url, name)


def add_nats_check(nats_url: str) -> None:
    """Add a NATS health check."""
    _health_checker.nats(nats_url)


def add_custom_check(name: str, check_fn: Callable) -> None:
    """Add a custom health check function."""
    _health_checker.add_custom_check(name, check_fn)


async def get_health_status() -> dict[str, Any]:
    """Get current health status."""
    return await _health_checker.check_all()


if FASTAPI_AVAILABLE:
    from fastapi import APIRouter

    health_check_router = APIRouter()

    @health_check_router.get(HEALTH_CHECK_PATH)
    async def healthz():
        """Standard health check endpoint."""
        return await get_health_status()

    def create_health_app(service_name: str | None = None) -> FastAPI:
        """Create a minimal FastAPI app with health check."""
        from fastapi import FastAPI
        app = FastAPI(title=service_name or 'PMOVES Service')
        app.include_router(health_check_router)
        return app
else:
    def create_health_app(service_name: str | None = None):
        """Raise error if FastAPI not available."""
        raise ImportError('FastAPI is required to create health app')


# Example usage
if __name__ == '__main__':
    async def example_usage():
        """Example of how to use the health checker."""

        # Create a health checker
        checker = HealthChecker('example-service')

        # Add checks
        checker.nats('nats://nats:4222')
        checker.http('http://supabase:8000', name='supabase')

        # Add custom check
        async def check_memory():
            import psutil
            return psutil.virtual_memory().percent < 90

        checker.add_custom_check('memory_ok', check_memory)

        # Run checks
        status = await checker.check_all()
        print(status)

    asyncio.run(example_usage())
