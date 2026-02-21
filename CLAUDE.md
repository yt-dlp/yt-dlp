# PMOVES.YT Developer Context

**Always-on context for Claude Code CLI when working in the PMOVES.YT repository.**

## Architecture Overview

PMOVES.YT is a **YouTube ingestion and processing service** that:
- Downloads videos via yt-dlp with configurable quality/format
- Stores media in MinIO S3-compatible object storage
- Retrieves/generates transcripts (YouTube captions or Whisper)
- Publishes NATS events for downstream processing
- Tracks ingestion state in Supabase

## Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `app/main.py` | `app/` | FastAPI server, route handlers |
| `app/yt.py` | `app/` | Core yt-dlp download logic |
| `app/transcript.py` | `app/` | Transcript retrieval and processing |
| `app/minio_client.py` | `app/` | MinIO storage operations |
| `app/nats_publisher.py` | `app/` | NATS event publishing |
| `app/supabase_client.py` | `app/` | Supabase state tracking |
| `bundle/` | `bundle/` | yt-dlp bundled configuration |

## Security Posture

- **P1 FIXED:** USER directive present (Jan 28 P2 satisfied)
- **P2 OPEN:** MinIO default credentials (`minioadmin/minioadmin`) in env defaults
- **P2 OPEN:** Query injection risk — URL parameters not fully sanitized in `yt.py`
- **GREEN:** Excellent Docker hardening (cap_drop ALL, read_only, tmpfs mounts)
- **GREEN:** `/healthz` health check endpoint
- **GREEN:** `/metrics` Prometheus endpoint

## APIs

### HTTP API (Port 8077)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/healthz` | GET | Health check |
| `/metrics` | GET | Prometheus metrics |
| `/yt/ingest` | POST | Ingest a YouTube video |
| `/yt/status` | GET | Check ingestion status |
| `/yt/channels` | GET | List monitored channels |
| `/yt/channels` | POST | Add channel for monitoring |

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
pip install -r requirements.txt

uvicorn app.main:app --host 127.0.0.1 --port 8077
```

### Docker

```bash
# With PMOVES.AI (docked mode)
# Managed by parent docker-compose with profile: yt
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
- **Port:** 8077
- **Networks:** `pmoves-net`, `data-net`
- **Depends on:** NATS, MinIO, Supabase (all `service_healthy`)

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
