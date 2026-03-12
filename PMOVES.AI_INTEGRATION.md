# PMOVES.YT Integration Guide

PMOVES.YT is now the authoritative PMOVES YouTube ingest runtime. PMOVES.AI should consume this submodule directly for the `pmoves-yt` image/runtime instead of maintaining a separate root implementation as the source of truth.

## Canonical runtime

Authoritative files:
- `pmoves_yt_service/yt.py`
- `pmoves_yt_service/docs_sync.py`
- `pmoves_yt_service/docs_catalog.py`
- `pmoves_yt_service/Dockerfile`
- `docs/RUNTIME.md`

Root PMOVES.AI keeps `pmoves/services/pmoves-yt` only as a compatibility mirror/shim for local imports and older docs links.

## Compose consumption

Root compose should build `pmoves-yt` from this repo:

```yaml
pmoves-yt:
  build:
    context: ../PMOVES.YT
    dockerfile: pmoves_yt_service/Dockerfile
    args:
      YTDLP_VERSION: ${YTDLP_VERSION:-}
      YTDLP_PIP_URL: ${YTDLP_PIP_URL:-}
```

See `pmoves_yt_service/README.md` for the full build-arg contract and operator examples.

## Runtime contract

Primary endpoints:
- `GET /healthz`
- `GET /metrics`
- `POST /yt/ingest`
- `POST /yt/emit`
- `GET /yt/emit/status/{job_id}`
- `GET /yt/docs/catalog`
- `POST /yt/docs/sync`

Core dependencies:
- Supabase/PostgREST for metadata + docs sync
- MinIO/S3-compatible object storage for media artifacts
- Hi-RAG v2 for indexing and geometry publication
- ffmpeg-whisper for transcript generation
- NATS for event publication
- channel-monitor for queue/status integration
- Invidious + companion for throttling/SABR fallback
- Jellyfin backfill via `/yt/search`

## Production notes

- `pmoves_yt_service/docs_catalog.py` is the authoritative source for yt-dlp option/extractor metadata exposed to the UI and agents.
- `pmoves_yt_service/docs_sync.py` is the authoritative source for syncing yt-dlp docs into `pmoves_core.tool_docs`.
- The root repo should validate this submodule with service health plus `/yt/docs/catalog`, not just container liveness.

## Validation

```bash
curl http://localhost:8077/healthz
curl http://localhost:8077/yt/docs/catalog
curl -X POST http://localhost:8077/yt/docs/sync -H 'X-API-Key: YOUR_API_KEY'
python -m pytest -q pmoves_yt_service/tests
```
