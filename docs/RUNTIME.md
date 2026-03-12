# PMOVES.YT Runtime

PMOVES.YT is the authoritative PMOVES YouTube ingest runtime and the upstream yt-dlp fork consumed by PMOVES.AI.

Canonical runtime files:
- `pmoves_yt_service/yt.py`
- `pmoves_yt_service/docs_sync.py`
- `pmoves_yt_service/docs_catalog.py`
- `pmoves_yt_service/Dockerfile`

Runtime model:
- PMOVES.AI consumes this repo as a submodule and builds `pmoves-yt` from here.
- `pmoves/services/pmoves-yt` in the root repo is a compatibility mirror only.
- `/yt/docs/catalog` and `/yt/docs/sync` are owned here.

Local build:

```bash
docker build -f pmoves_yt_service/Dockerfile -t pmoves-yt:dev .
```

Local run:

```bash
docker run --rm -p 8077:8077 pmoves-yt:dev
```

Primary validation:

```bash
curl http://localhost:8077/healthz
curl http://localhost:8077/yt/docs/catalog
ruff check pmoves_yt_service
python -m pytest -q pmoves_yt_service/tests
```

Downloader/runtime notes:
- Default submodule client chain: `YT_PLAYER_CLIENT=default,mweb`
- Production root compose may override that to `web_safari` with an aligned Safari UA
- Prefer `BGUTIL_HTTP_BASE_URL` or companion-backed tokens over static `YT_PO_TOKEN_VALUE`
- If `YT_ENABLE_PO_TOKEN=true`, tokens must follow yt-dlp's `client.context+token` contract
