# YT-Studio

YT-Studio is a native Windows desktop GUI for yt-dlp.

## Development

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the app:

```powershell
python main.py
```

Run tests:

```powershell
python -m pytest tests -q
```

Build a Windows executable:

```powershell
pyinstaller YTStudio.spec
```

Place `ffmpeg.exe` in `assets/` before building if you want it bundled with the executable.
