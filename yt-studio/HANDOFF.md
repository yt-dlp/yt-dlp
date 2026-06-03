# YT-Studio Handoff

## Current Shape

YT-Studio is a PySide6 Windows desktop GUI built beside the local yt-dlp engine. The app entry point is `main.py`; the main shell is `gui/main_window.py`; the download screen is `gui/download_tab.py`; queue management is in `gui/queue_tab.py`; yt-dlp option conversion is centralized in `core/options.py`.

## Recent Fixes

- Queue management has visible controls for start, pause, resume, done, remove, and clear done.
- Queue rows keep a real `DownloadJob` object, so resume restarts the same job with yt-dlp continuation enabled.
- Start All now works as a sequential queue runner. When one queued job finishes, the next waiting job starts automatically.
- Direct Download Now no longer stops after adding a job to the queue. The previous bug was an undefined `output_dir` variable inside `DownloadTab.start_job()`.
- The download screen snapshots a job before starting it. Fetching a new URL updates only the fetch/media panel and does not overwrite active download status/progress.
- Fetching shows an animated `FETCHING DATA...` line above the download status bar.
- Post-processing errors after a completed yt-dlp download hook are treated as completed downloads with a warning instead of failed downloads. This avoids the misleading "Error opening output files" failure when the media file already exists.
- Rivestream URLs with browser-escaped query strings such as `&amp;id=` are normalized and handled by `yt_dlp.extractor.rivestream`.
- Rivestream movie, TV, series, show, anime, and cartoon URLs are routed through Rivestream metadata and then StreamIMDb. TV-like URLs use `season` and `episode` query parameters, defaulting to S1E1 when they are missing.
- Subtitle search was added through `core/subtitles.py` with Wyzie and SubDL provider support. It can search English or Arabic by IMDb/TMDB/current media ID and save a selected subtitle beside the output file. Both providers currently require API keys, so the Config screen has `WYZE/WYZIE SUBS API KEY` and `SUBDL SUBS API KEY` fields.
- `core/runtime.py` detects bundled `assets/ffmpeg.exe`; `core/options.py` uses it automatically when the user has not configured an external FFmpeg path.

## Subtitle Providers

Providers currently wired into the app:

- Wyzie Subs (`https://sub.wyzie.ru/search`): aggregates common subtitle sources, but currently requires an API key.
- SubDL (`https://api.subdl.com/api/v1/subtitles`): supports IMDb/TMDB search, movie/TV type, season/episode, and language filtering; requires an API key.

Credible optional providers for future expansion:

- OpenSubtitles REST API: strong coverage, but requires API credentials.
- SubSource API: movie/TV subtitle API with profile-created API keys.

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
.\.venv\Scripts\python.exe -m pytest tests --basetemp E:\Users\DELL\doc\dw\pytest-temp\ytstudio-original
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
- `core/subtitles.py`: subtitle provider URL building, result parsing, search/download workers.
- `yt_dlp/extractor/rivestream.py`: Rivestream movie and TV/series routing.
- `yt_dlp/extractor/streamimdb.py`: StreamIMDb direct extraction and season/episode query handling.
