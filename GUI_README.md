# yt-dlp GUI für Windows

Die GUI wird als einzelne Datei `dist/yt-dlp-GUI.exe` gebaut. Auf dem Zielcomputer werden weder Python noch yt-dlp oder ffmpeg benötigt.

## EXE bauen

PowerShell im Repository öffnen und ausführen:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_gui.ps1
```

Das Skript installiert PyInstaller in der Entwicklungsumgebung, lädt die Windows-Version von FFmpeg herunter und bettet `ffmpeg.exe` sowie `ffprobe.exe` in die EXE ein.

Die fertige Datei liegt anschließend unter `dist\yt-dlp-GUI.exe`.

## Funktionen

- Video-, Audio- und Playlist-Downloads
- MP3-Extraktion
- Auswahl des Ausgabeordners
- Fortschritt, Geschwindigkeit und ETA
- Abbrechen laufender Downloads
- Optionale Untertitel mit Sprachauswahl, Vorschaubilder, Metadaten und JSON-Infos
- Kapitel, Beschreibung, Kommentare und wählbare MP3-Qualität
- Kompaktes festes Layout mit bis zu 10 parallelen Stream-Fragmenten
- Keine separate Installation auf dem Zielcomputer

Die Nutzung muss den Bedingungen der jeweiligen Plattform und den Rechten am heruntergeladenen Inhalt entsprechen. FFmpeg wird unter dessen eigener Lizenz weitergegeben; die zugehörigen Lizenzinformationen sollten beim Verteilen der EXE mitgeliefert werden.
