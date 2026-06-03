"""FastAPI app: mounts provider-scoped routers."""

import os

from fastapi import FastAPI

from api.routes import router as api_router


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


def _limit_extraction_concurrency() -> None:
    """Cap how many sync (extraction) endpoints run at once.

    FastAPI runs sync `def` handlers in AnyIO's threadpool, which defaults to 40
    tokens — i.e. up to 40 concurrent yt-dlp extractions in a single process.
    Each extraction is memory-heavy, so a burst can blow past the instance's RAM
    limit (OOM). Lower the token count to bound peak memory; excess requests
    queue cheaply at the ASGI layer. The `/health` route is async, so it runs on
    the event loop and is never blocked by busy extraction threads.
    """
    try:
        import anyio.to_thread
    except ImportError:
        return
    try:
        tokens = int(os.environ.get('MAX_CONCURRENT_EXTRACTIONS', '4'))
    except ValueError:
        tokens = 4
    if tokens > 0:
        anyio.to_thread.current_default_thread_limiter().total_tokens = tokens


app = FastAPI(
    title='yt-dlp Metadata API',
    description='HTTP API for video metadata (no download). Extensible to more providers and data types.',
    on_startup=[_load_env, _limit_extraction_concurrency],
)


@app.get('/health')
async def health() -> dict[str, str]:
    """Unauthenticated health check for Render and load balancers.

    Async so it runs on the event loop, not the (capped) extraction threadpool —
    stays responsive even when all extraction slots are busy.
    """
    return {'status': 'ok'}


app.include_router(api_router)
