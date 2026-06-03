# yt-dlp Metadata API

HTTP API for video metadata only (no download). Uses yt-dlp extraction under the hood.

## Install

From the repo root:

```bash
pip install -e ".[api]"
```

## Run

```bash
yt-dlp-api
```

Or:

```bash
python -m api
```

Environment variables:

- `YT_DLP_API_HOST` (default: `127.0.0.1`) – bind address
- `YT_DLP_API_PORT` (default: `8000`) – port (or `PORT` on Render)
- `MAX_CONCURRENT_EXTRACTIONS` (default: `4`) – max yt-dlp extractions running at once per worker process. Caps peak memory (each extraction is memory-heavy); requests beyond the limit queue. Lower it if you still hit OOM, raise it if you have RAM to spare. The `/health` check is async and unaffected.
- **`YT_DLP_API_SECRET`** (required) – secret used to authenticate requests; must be sent as a Bearer token (see below)
- **`PROXY_APIFY_PASSWORD`** (optional) – when set, all extraction requests use [Apify residential proxy](https://docs.apify.com/platform/proxy/residential-proxy) (`groups-RESIDENTIAL`). Use this in production (e.g. on Render) to reduce YouTube “Sign in to confirm you’re not a bot” errors. Get the password from [Apify Proxy](https://console.apify.com/proxy). On Render, add `PROXY_APIFY_PASSWORD` in the service **Environment** with your Apify proxy password.
- **`TIKTOK_DEVICE_ID`** (optional) – 19-digit device ID for the TikTok mobile API. Required for **hashtag posts** (`GET /tiktok/hashtag/posts`); user profile and user posts work without it. To find a working value: search [yt-dlp GitHub issues](https://github.com/yt-dlp/yt-dlp/issues?q=tiktok+device_id) for "tiktok" and "device_id", or try a 19-digit number in the range the extractor uses (e.g. 7250000000000000000–7325099899999994577). TikTok may invalidate IDs over time. **Note:** Hashtag posts may still return 503 if TikTok requires X-Gorgon/signature headers (yt-dlp does not generate these).

Example: `YT_DLP_API_PORT=9000 yt-dlp-api`

### Authentication

Every request must include the shared secret in the **Authorization** header as a Bearer token:

```http
Authorization: Bearer YOUR_API_SECRET
```

Set `YT_DLP_API_SECRET` in your environment (e.g. in a `.env` file locally). **On Render:** open your service → **Environment** → add a variable `YT_DLP_API_SECRET` with your chosen secret (Render will inject it at runtime). If `YT_DLP_API_SECRET` is not set, the API returns 503.

Example with curl:

```bash
curl -H "Authorization: Bearer YOUR_API_SECRET" "http://127.0.0.1:8000/youtube/video?url=..."
```

## Endpoints (initial)

| Method | Path | Description |
|--------|------|--------------|
| GET | `/youtube/channel/videos?url=...` | Flat list of videos for a channel/playlist (same shape as `yt-dlp --flat-playlist -j`) |
| GET | `/youtube/video?url=...` | Full video metadata (includes `game`, `game_url`, `game_release_year` when present) |

Example (include the Bearer token):

```bash
curl -H "Authorization: Bearer YOUR_API_SECRET" "http://127.0.0.1:8000/youtube/channel/videos?url=https://www.youtube.com/channel/UCWB7gLoqYpMNewM084K6mFQ/recent"
curl -H "Authorization: Bearer YOUR_API_SECRET" "http://127.0.0.1:8000/youtube/video?url=https://www.youtube.com/watch?v=VIDEO_ID"
```

## Upstream compatibility

The API lives in the `api/` package and does not modify `yt_dlp/`. When you pull from the core yt-dlp repository, only core files change; you can keep the API layer and update it as needed.

## Extensibility

- **More providers (e.g. Twitch)**: Add `api/routes/twitch.py` with prefix `"/twitch"` and routes that validate Twitch URLs and call `service.extract(url, "<type>")`.
- **More data types**: Add a new `extract_type` in `api/service.py` (e.g. `"search"`, `"comments"`), wire the right yt-dlp options, then add a new route under the right provider (e.g. `GET /youtube/search`).
