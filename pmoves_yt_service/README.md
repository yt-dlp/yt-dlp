# PMOVES.YT — Ingest + CGP Publisher

YouTube ingest helper that emits CHIT geometry after analysis.

## Service & Ports

- Compose service: `pmoves-yt`
- Starts with `make up-yt` (brings up `ffmpeg-whisper` too)

## Geometry Bus (CHIT) Integration

- Publishes `geometry.cgp.v1` to the Hi‑RAG gateway:
  - Endpoint: `POST ${HIRAG_URL}/geometry/event`
- Environment:
  - `HIRAG_URL` — base URL for the geometry gateway (`http://localhost:8086` by default)

## Smoke

- See `pmoves/services/pmoves-yt/tests/test_emit.py` for the CGP emission assertion.
- Run the main smokes in `pmoves/docs/SMOKETESTS.md` after `make up`.

## Testing

- Unit suite: `python -m pytest pmoves/services/pmoves-yt/tests`
- Overlay lint: `ruff check pmoves_yt_service`
- Offline bundle refresh: `make vendor-httpx` (requires [uv](https://github.com/astral-sh/uv)) rebuilds `pmoves/vendor/python/` so helper scripts like `pmoves/scripts/backfill_jellyfin_metadata.py` can import `httpx` without pip.

## Modern downloader path

- Default PMOVES.YT client selection now follows `default,mweb` unless `YT_PLAYER_CLIENT` overrides it.
- Prefer bgutil POT provider wiring (`BGUTIL_HTTP_BASE_URL`) over static `YT_PO_TOKEN_VALUE`.
- If `YT_ENABLE_PO_TOKEN=true`, PMOVES.YT normalizes raw or legacy tokens into yt-dlp's current `client.context+token` format before applying extractor args.
- Root `PMOVES.AI` compose intentionally overrides the runtime with `web_safari` + a Safari UA for the current production stack. Keep submodule and root docs aligned when changing that override.
- Invidious Companion remains the first fallback for throttled YouTube downloads when configured; plain Invidious stays the secondary fallback.

## Read vs write control plane

- PMOVES.YT's current production strength is read/ingest:
  - yt-dlp for metadata/media extraction
  - companion/Invidious for fallback download paths
  - Supabase + NATS + Jellyfin handoff for downstream PMOVES workflows
- PMOVES.YT is not yet the owned-channel write/control plane:
  - full playlist/channel lifecycle management
  - comment/reply actions
  - broader YouTube channel management
- Those creator-control actions should be implemented through the YouTube Data API with separate
  Google credentials and explicit approval/audit hooks, rather than trying to extend yt-dlp for
  write operations it is not designed to own.

### Initial owned-channel control endpoints

- `GET /yt/control/status`
  - reports whether Google client credentials, a default refresh token, and approval gating are configured
- `POST /yt/control/playlist/add`
  - preview or execute adding a video to a playlist
- `POST /yt/control/playlist/create`
  - preview or execute creating a playlist
- `POST /yt/control/playlist/update`
  - preview or execute updating playlist title, description, or privacy
- `POST /yt/control/playlist/delete`
  - preview or execute deleting a playlist
- `POST /yt/control/playlist/remove`
  - preview or execute removing an item from a playlist
- `POST /yt/control/playlist/reorder`
  - preview or execute moving an existing playlist item to a new position
- `POST /yt/control/comment`
  - preview or execute a top-level comment or reply (`parent_comment_id` switches to reply mode)
- `POST /yt/control/comment/delete`
  - preview or execute deleting a comment or reply
- These endpoints:
  - are protected by the same `X-API-Key` gate used by docs sync when API keys are configured
  - default to preview mode (`execute=false`)
  - require `approved_by` when `YT_CONTROL_REQUIRE_APPROVAL=true` and `execute=true`
  - use the YouTube Data API, not yt-dlp
  - append audit records to `pmoves_core.youtube_control_actions` when the Supabase migration is applied
  - are designed to receive review-filtered payloads from `channel-monitor`, which now strips
    notebook/draft metadata before the live YouTube API call

## Resilient Playlist Ingest (2025-10)

- `/yt/playlist` now runs downloads concurrently (bounded by `YT_CONCURRENCY`) with
  an async worker pool and coordinated rate limiting (`YT_RATE_LIMIT`).
- Transient errors (network, 5xx, yt-dlp hiccups) retry with exponential backoff
  up to `YT_RETRY_MAX` attempts; state updates live in Supabase (`yt_items`).
- Downloads resume automatically thanks to a persistent scratch directory
  (`YT_TEMP_ROOT`, default `/tmp/pmoves-yt`). Successful ingests clean the cache;
  failures leave partial files to resume on the next run.
- Video metadata is enriched with duration, channel details, tags, statistics,
  and provenance (job id, timestamps) so downstream dashboards can render richer
  context without manual joins.
- Summaries/chapters emit `ingest.summary.ready.v1` / `ingest.chapters.ready.v1`
  events so downstream automations (Discord, n8n) can react in real time.

## Channel Monitor Enrichment (2025-10-26)

- `pmoves.channel_monitor` now forwards detailed channel metadata with each
  queue payload. pmoves-yt persists the enriched context into the
  `youtube_transcripts` table via new columns:
  - `channel_id`, `channel_url`, `channel_thumbnail`
  - `channel_tags` (text array) and `namespace`
  - `channel_metadata` (JSONB with priority + subscriber counts)
- The `meta` JSON payload also stores the raw `channel_monitor` metadata so
  downstream RAG jobs can audit ingestion history or render richer UI chrome.
- Use the metadata to filter notebook syncs or n8n workflows by brand/namespace
  without additional joins — e.g. `channel_tags @> '{"darkxside"}'`.

### yt-dlp configuration & images (2025-12)

- `yt-dlp[default]` + `curl-cffi` ship from PyPI at build time; `ffmpeg` and `atomicparsley`
  are installed via apt so metadata/thumbnail embedding works out of the box.
- Build args:
  - `YTDLP_VERSION=YYYY.MM.DD` to pin an exact release.
  - `YTDLP_PIP_URL=<pip URL>` to consume a fork (e.g., git+https). `YTDLP_PIP_URL` wins over `YTDLP_VERSION`.
- Weekly bump workflow `.github/workflows/yt-dlp-bump.yml` opens a PR with the latest yt-dlp and validates a multi-arch GitHub build.
  Override or skip by supplying your own `YTDLP_VERSION`/`YTDLP_PIP_URL` in image builds.

Example:

```bash
# Pin by version
docker build --build-arg YTDLP_VERSION=2025.10.15 -t ghcr.io/powerfulmoves/pmoves-yt:dev services/pmoves-yt

# Or install from a fork/commit (full pip URL)
docker build --build-arg YTDLP_PIP_URL='git+https://github.com/POWERFULMOVES/yt-dlp.git@main#egg=yt-dlp[default]' \
  -t ghcr.io/powerfulmoves/pmoves-yt:dev services/pmoves-yt
```

#### Fork & GHCR for reproducible builds

We maintain a fork to stabilize SABR/nsig workarounds and keep yt‑dlp fresh:

- Repo: https://github.com/POWERFULMOVES/PMOVES.YT.git
- Helpers from repo root:

```bash
make -C pmoves yt-integrations-clone
make -C pmoves yt-integrations-build YTDLP_VERSION=2025.10.15
make -C pmoves yt-integrations-push

# Use the published image in compose
export PMOVES_YT_IMAGE=ghcr.io/powerfulmoves/pmoves-yt:dev
make -C pmoves up-yt
```

The compose service honors `PMOVES_YT_IMAGE` (pulls from GHCR) or builds from
`services/pmoves-yt` when unset. Use the `yt-image-local` make target to build
and tag a local image quickly with a custom `YTDLP_VERSION`.
- `YT_ARCHIVE_DIR` (default `/data/yt-dlp`) + `YT_ENABLE_DOWNLOAD_ARCHIVE=true`
  configure yt-dlp's archive file. Override per channel with
  `yt_options.download_archive` to dedupe imports per playlist.
- `YT_SUBTITLE_LANGS` (comma separated) `YT_SUBTITLE_AUTO` pull caption tracks;
  pass `yt_options.subtitle_langs` per channel to mix languages.
- `YT_WRITE_INFO_JSON` (default true) stores the `.info.json` artifact; disable
  with `yt_options.write_info_json=false` when not needed.
- `YT_POSTPROCESSORS_JSON` lets you override the default postprocessor list
  (`FFmpegMetadata` + `EmbedThumbnail`). Leave empty (`[]`) to skip embedding.
  Channel configs can set `yt_options.postprocessors` for one-off tweaks.

### Keep yt-dlp options discoverable (docs → Supabase)

Docs sync is protected by `X-API-Key` when `VALID_API_KEYS` is configured and
throttled by `YT_DOCS_SYNC_MIN_INTERVAL_SECONDS` (default `30` seconds).

To surface the full, current yt‑dlp CLI options to the UI and automations,
pmoves-yt can ingest its own help into Supabase:

```bash
curl -X POST http://localhost:8077/yt/docs/sync \
  -H 'X-API-Key: YOUR_API_KEY'
```

This captures `yt-dlp --help`, `--list-extractors`, and `--dump-user-agent` and
upserts them into `pmoves_core.tool_docs` keyed by `(tool, version, doc_type)`.
Ensure the Supabase REST URL/key env vars are set (compose does this by default).

### Options Catalog endpoint (new)


- `GET /yt/docs/catalog` returns:
  - `meta.yt_dlp_version`, `meta.extractor_count`
  - a structured `options[]` catalog (flags, dest, help, default, choices)
  - counts for quick UI rendering

### Automatic docs sync


- Env: `YT_DOCS_SYNC_ON_START=true` to sync on container start (default true)
- Env: `YT_DOCS_SYNC_INTERVAL_SECONDS=86400` to enable periodic sync

### Using external yt-dlp configs (new)

If you have a classic `yt-dlp` `config.txt`, convert it into a `yt_options` JSON
that this service understands:

```bash
python pmoves/services/pmoves-yt/tools/ytdlp_config_to_options.py \
  pmoves/docs/PMOVES.AI\ PLANS/PMOVES.yt/yt-dlp-config/config.txt \
  > /tmp/yt_options.json

curl -sS -X POST http://localhost:8077/yt/download \
  -H 'content-type: application/json' \
  -d @/tmp/yt_options.json | jq .
```

The converter maps common flags (`-f`, `--merge-output-format`, `--sub-langs`,
`--write-auto-subs`, `--sponsorblock-*`, `--download-archive`, retries/pacing,
cookies, and embed postprocessors) into the `yt_options` structure while leaving
unknown flags out for safety. See the detailed mapping and caveats in:

- `pmoves/docs/PMOVES.AI PLANS/PMOVES.yt/YTDLP_CONFIG_ADAPTATION.md`


## Hi‑RAG upsert pacing (2025-10-24)

- `/yt/emit` switches to a background task when `YT_ASYNC_UPSERT_ENABLED=true` and the
  segmented chunk count ≥ `YT_ASYNC_UPSERT_MIN_CHUNKS` (defaults: enabled, 200 chunks).
  The API response returns `{"async": true, "job_id": "..."}`; poll
  `/yt/emit/status/{job_id}` for completion or failure details.
- `YT_INDEX_LEXICAL_DISABLE_THRESHOLD` (default `0`) disables the Meili/lexical index
  step automatically for very large transcripts so the request can return quickly.
- `YT_UPSERT_BATCH_SIZE` (default `200`) defines how many chunks each
  `/hirag/upsert-batch` call carries. Tune alongside the lexical threshold when
  dealing with hour-long transcripts.
- Build provenance in healthz

- `GET /healthz` returns `{ ok: true, yt_dlp: { yt_dlp_version }, provenance: { channel, origin, ytdlp_arg_version, ytdlp_pip_url } }`.
- Set `YT_CHANNEL`/`YT_ORIGIN` during integration builds (the upstream bundle uses `CHANNEL`/`ORIGIN`; both names are read).
