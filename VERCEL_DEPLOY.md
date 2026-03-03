# Deploy this yt-dlp fork to Vercel (with Web UI)

This fork can be deployed to Vercel and used directly in the browser:

1. Open your fork in GitHub.
2. In Vercel, click **Add New Project**.
3. Import your fork repository.
4. Deploy with default settings.

After deploy, visit your project URL and use the form on `/`.

## What is included

- `index.html` → Web UI where you paste links and request a download URL.
- `api/download.py` → serverless API route that uses yt-dlp to resolve a direct media URL.
- `vercel.json` → function runtime/duration config.

## Supported links

- YouTube links
- X/Twitter links
- Many other extractors supported by yt-dlp

## Important limits

- Vercel functions are short-lived. Some URLs can timeout.
- Private/age-restricted/rate-limited content may require cookies/auth.
- This setup resolves direct media URLs. For very large/long jobs, use a worker/container platform.

## Local run

You can preview the UI locally:

```bash
python -m http.server 8000
# open http://localhost:8000
```

To run serverless routes locally, use Vercel CLI:

```bash
vercel dev
```
