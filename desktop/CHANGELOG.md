# Changelog

All notable changes to Dubdeck. Versions follow semantic versioning.

## 1.0.0 (2026-11-15)

First release.

- Downloads queue with parallel downloads, progress, speed, time left, pause and resume (survives quitting), cancel with clean-up, retry, scheduling, and automatic retry when the connection drops.
- Link previews with formats, subtitles and a playlist item picker.
- Simple mode, and an Advanced mode covering all 250 documented engine options with plain-English explanations, search and a live command preview. The 73 hidden and deprecated flags work through Extra arguments.
- Presets (six built in), yt-dlp config-file import and export, and options applied to every download.
- Plain-language error explanations for 31 known failure types, the stage that failed, one-click fixes, and a redacted problem report.
- Checks before starting that catch option combinations the engine cannot handle without a terminal.
- Engine screen: checksum-verified engine updates from several channels, revert to the bundled engine, ffmpeg install, and every one-off engine command.
- Built-in app updater (GitHub releases).
- Searchable history, a Logs screen and persistent per-download logs with secrets removed.
- Welcome guide, Help screen, keyboard shortcuts, drag and drop, light and dark themes.
- Installers for Windows (installer and portable), macOS (dmg) and Linux (AppImage, deb, tar.gz) with the engine and ffmpeg inside.
