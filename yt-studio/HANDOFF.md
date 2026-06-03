# YT-Studio Handoff

## Current Shape

YT-Studio is a PySide6 Windows desktop GUI built beside the local yt-dlp engine. The app entry point is `main.py`; the main shell is `gui/main_window.py`; the download screen is `gui/download_tab.py`; queue management is in `gui/queue_tab.py`; yt-dlp option conversion is centralized in `core/options.py`.

## Recent Fixes

- Queue management now has visible controls for start, pause, resume, done, remove, and clear done.
- Queue rows keep a real `DownloadJob` object, so resume restarts the same job with yt-dlp continuation enabled.
- The download screen snapshots a job before starting it. Fetching a new URL updates only the fetch/media panel and no longer overwrites active download status/progress.
- Fetching shows an animated `FETCHING DATA...` line above the download status bar.
- Post-processing errors after a completed yt-dlp download hook are treated as completed downloads with a warning instead of failed downloads. This avoids the misleading “Error opening output files” failure when the movie file already exists.
- Rivestream URLs with browser-escaped query strings such as `&amp;id=` are normalized and handled by `yt_dlp.extractor.rivestream`.
- Subtitle search was added through `core/subtitles.py` with Wyzie Subs as the default provider. It can search English or Arabic by IMDb/TMDB/current media ID and save a selected subtitle beside the output file. Wyzie currently returns HTTP 401 without an API key, so the Config screen has a `WYZE/WYZIE SUBS API KEY` field.
- `core/runtime.py` detects bundled `assets/ffmpeg.exe`; `core/options.py` uses it automatically when the user has not configured an external FFmpeg path.

## Subtitle Providers

Default provider: Wyzie Subs (`https://sub.wyzie.ru/search`). It aggregates common sources including OpenSubtitles-compatible results, but currently requires a free API key.

Credible optional providers for future expansion:

- OpenSubtitles REST API: strong coverage, but requires API credentials.
- SubDL API: good Subscene-style coverage, but requires an API key.

Do not promise a no-key subtitle API unless it is verified live. In 2026, the credible subtitle APIs checked for this app require credentials or rate-limited access.

## Portable FFmpeg

For a fully portable EXE, place `ffmpeg.exe` at:

```text
yt-studio/assets/ffmpeg.exe
```

`YTStudio.spec` bundles this file when present. At runtime, `core.runtime.bundled_ffmpeg_path()` finds the extracted PyInstaller asset and `build_ydl_options()` passes its folder to yt-dlp as `ffmpeg_location`.

## Test Commands

From the repo root:

```powershell
python -m pytest yt-studio\tests
python -m pytest test\test_all_urls.py -k "rivestream or streamimdb"
```

If PySide6 is missing from system Python, use the app virtual environment:

```powershell
cd C:\Users\DELL\.openclaw\workspace\dw\v2\yt-studio
.\.venv\Scripts\python.exe -m pytest tests --basetemp C:\tmp\ytstudio-pytest
```

## Build Command

From `yt-studio`:

```powershell
$env:YTSTUDIO_YTDLP_ENGINE="..\"
$env:PYTHONPATH="..\"
python -m PyInstaller --clean --noconfirm YTStudio.spec
```

For the original local app folder, set `YTSTUDIO_YTDLP_ENGINE` and `PYTHONPATH` to:

```text
C:\Users\DELL\.openclaw\workspace\dw\v2\yt-dlp-2026.03.17\yt-dlp-2026.03.17
```

## Important Files

- `gui/download_tab.py`: active download, fetch animation, subtitle search/download, queue callbacks.
- `gui/queue_tab.py`: queue table and queue controls.
- `core/downloader.py`: yt-dlp worker, progress hooks, completed-with-warning handling.
- `core/options.py`: all GUI-to-yt-dlp option mapping, including bundled FFmpeg.
- `core/subtitles.py`: subtitle search/download workers.
- `yt_dlp/extractor/rivestream.py`: Rivestream URL handling.
- `yt_dlp/extractor/streamimdb.py`: StreamIMDb direct extraction.
