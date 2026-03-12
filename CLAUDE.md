# PMOVES.YT Developer Context

**Always-on context for Claude Code CLI when working in the PMOVES.YT repository.**

## Architecture Overview

PMOVES.YT now has two responsibilities in one repo:
- the upstream `yt_dlp/` fork consumed for extraction/runtime packaging
- the authoritative PMOVES service package in `pmoves_yt_service/`

PMOVES.AI should treat this repo as the source of truth for:
- video metadata and download handling via yt-dlp
- transcripts, summaries, chapter generation, and `/yt/emit`
- yt-dlp docs sync and structured options catalog
- the image/runtime built for the `pmoves-yt` service in the parent compose stack

## Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `pmoves_yt_service/yt.py` | `pmoves_yt_service/` | FastAPI server + PMOVES ingest pipeline |
| `pmoves_yt_service/docs_sync.py` | `pmoves_yt_service/` | yt-dlp docs capture + Supabase sync |
| `pmoves_yt_service/docs_catalog.py` | `pmoves_yt_service/` | structured option/extractor catalog |
| `pmoves_yt_service/Dockerfile` | `pmoves_yt_service/` | authoritative PMOVES runtime image |
| `yt_dlp/` | `yt_dlp/` | upstream forked extractor/runtime code |
| `bundle/` | `bundle/` | yt-dlp bundled configuration |

## Security Posture

- **P1 FIXED:** USER directive present (Jan 28 P2 satisfied)
- **P2 OPEN:** MinIO default credentials (`minioadmin/minioadmin`) in env defaults
- **P2 OPEN:** Query injection risk — URL parameters not fully sanitized in `yt.py`
- **GREEN:** Excellent Docker hardening (cap_drop ALL, read_only, tmpfs mounts)
- **GREEN:** `/healthz` health check endpoint
- **GREEN:** `/metrics` Prometheus endpoint
- **GREEN:** `/yt/docs/catalog` returns live option/extractor metadata when the package is present

## APIs

### HTTP API (Port 8077)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/healthz` | GET | Health check |
| `/metrics` | GET | Prometheus metrics |
| `/yt/ingest` | POST | Ingest a YouTube video |
| `/yt/emit` | POST | Segment transcript and publish geometry/Hi-RAG updates |
| `/yt/emit/status/{job_id}` | GET | Check async emit status |
| `/yt/docs/catalog` | GET | Structured yt-dlp option + extractor metadata |
| `/yt/docs/sync` | POST | Upsert yt-dlp docs into Supabase |

### Ingest Request Format

```json
{
  "url": "https://www.youtube.com/watch?v=...",
  "quality": "best",
  "transcript": true,
  "archive": true
}
```

## NATS Subjects

| Subject | Direction | Purpose |
|---------|-----------|---------|
| `ingest.file.added.v1` | Publish | New file stored in MinIO |
| `ingest.transcript.ready.v1` | Publish | Transcript available |
| `ingest.summary.ready.v1` | Publish | AI summary generated |
| `ingest.chapters.ready.v1` | Publish | Chapter markers extracted |

## Configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| `NATS_URL` | NATS connection URL | `nats://nats:pmoves@nats:4222` |
| `MINIO_ENDPOINT` | MinIO server | `minio:9000` |
| `MINIO_ACCESS_KEY` | MinIO access key | Required |
| `MINIO_SECRET_KEY` | MinIO secret key | Required |
| `YT_CONCURRENCY` | Parallel downloads | `2` |
| `YT_ARCHIVE_DIR` | Download archive path | `/data/yt-dlp` |
| `YT_ENABLE_DOWNLOAD_ARCHIVE` | Skip already-downloaded | `true` |
| `YT_ENABLE_PO_TOKEN` | Use PO token for auth | `true` |
| `YT_TRANSCRIPT_PROVIDER` | Transcript source | `faster-whisper` |
| `YT_WHISPER_MODEL` | Whisper model size | `small` |
| `YT_SUBTITLE_LANGS` | Subtitle languages | `en` |
| `YT_ASYNC_UPSERT_ENABLED` | Async Supabase writes | `true` |
| `YT_ASYNC_UPSERT_MIN_CHUNKS` | Min chunks for async | `200` |
| `WHISPER_URL` | Whisper service URL | `http://ffmpeg-whisper:8078` |

## Development

### Local Setup

```bash
cd PMOVES.YT
pip install -r pmoves_yt_service/requirements.txt
pip install ".[default]"

uvicorn pmoves_yt_service.yt:app --host 127.0.0.1 --port 8077
```

### Docker

```bash
# With PMOVES.AI (docked mode)
# Managed by parent docker-compose with profile: yt
# Parent repo now builds from this submodule, not from a root shadow copy
```

### Testing

```bash
# Health check
curl http://localhost:8077/healthz

# Ingest a video
curl -X POST http://localhost:8077/yt/ingest \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

## PMOVES.AI Integration

### Docked Mode

- **Compose profile:** `yt`
- **Port:** `8077`
- **Build context:** `PMOVES.YT`
- **Dockerfile:** `pmoves_yt_service/Dockerfile`
- **Consumer:** root PMOVES.AI compose stack

### Processing Pipeline

```
YouTube URL
  -> PMOVES.YT (download + store)
  -> NATS: ingest.file.added.v1
  -> FFmpeg-Whisper (transcribe)
  -> NATS: ingest.transcript.ready.v1
  -> Extract Worker (embed + index)
  -> Publisher-Discord (notify)
```

### Channel Monitor Integration

Channel Monitor (`port 8097`) watches YouTube channels and posts new videos to PMOVES.YT's `/yt/ingest` endpoint automatically.

## Common Gotchas

1. **yt-dlp updates:** YouTube frequently changes API; keep yt-dlp updated
2. **PO tokens:** Required for some YouTube content; configure `YT_PO_TOKEN_VALUE`
3. **MinIO buckets:** `cataclysm-assets` and `cataclysm-outputs` must exist
4. **Download archive:** `YT_ENABLE_DOWNLOAD_ARCHIVE=true` prevents re-downloading
5. **Whisper models:** Larger models = better quality but more VRAM; `small` is the default
6. **NATS auth:** URL must include credentials: `nats://nats:pmoves@nats:4222`

<!-- PMOVES.AI-CONTEXT-TAGS -->
## PMOVES.AI Skill Hints

**Primary Skills:** `/yt:ingest-video`, `/yt:status`, `/yt:list-channels`, `/deploy:up`, `/health:quick`
**Context Files:** `services-catalog.md`, `nats-subjects.md`
**Domain Tags:** `media`, `ingestion`
**Context Tier:** 2 (On-Demand (Major Subsystem))
<!-- /PMOVES.AI-CONTEXT-TAGS -->
