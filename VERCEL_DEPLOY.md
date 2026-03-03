# Deploy this yt-dlp fork to Vercel (with Web UI)

This fork can be deployed to Vercel and used directly in the browser:

1. Open your fork in GitHub.
2. In Vercel, click **Add New Project**.
3. Import your fork repository.
4. Deploy with default settings.

After deploy, visit your project URL and use the form on `/`.

## What is included

- `index.html` → Web UI where you paste links and click Download.
- `api/download.py` → resolves media metadata/link via yt-dlp.
- `api/fetch.py` → server-side proxied download endpoint (`Content-Disposition: attachment`).

## Why this fixes your 401 problem

Some providers (especially X/Twitter broadcasts) return signed media URLs that require request headers/tokens and fail with `401 unauthorized` when opened directly in a browser tab.

This project now uses `/api/fetch` to re-resolve and stream the file from the server, so pressing **Download** starts an actual browser file download instead of requiring you to open the raw media URL manually.

## Supported links

- YouTube links
- X/Twitter links
- Many other extractors supported by yt-dlp

## Important limits

- Vercel functions are short-lived. Large downloads may timeout.
- Private/age-restricted/rate-limited content may require cookies/auth.
- For heavy long-running downloads, use a worker/container platform.

## Local run

UI preview only:

```bash
python -m http.server 8000
```

Full local function emulation:

```bash
vercel dev
```

## Troubleshooting: runtime-version error

If Vercel build fails with `Function Runtimes must have a valid version`:

- Ensure you are deploying the **latest commit** from your branch.
- Remove any custom runtime/build overrides in Vercel project settings.
- Trigger a fresh deploy without cache.
