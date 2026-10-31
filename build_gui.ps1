$ErrorActionPreference = 'Stop'

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host 'yt-dlp GUI wird gebaut ...'

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'Python 3.11 oder neuer wurde nicht gefunden.'
}

python -m pip install --upgrade pyinstaller
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller konnte nicht installiert werden.' }

New-Item -ItemType Directory -Force -Path tools | Out-Null
$ffmpeg = Join-Path (Get-Location) 'tools\ffmpeg.exe'
$ffprobe = Join-Path (Get-Location) 'tools\ffprobe.exe'

if (-not (Test-Path $ffmpeg) -or -not (Test-Path $ffprobe)) {
    $archive = Join-Path $env:TEMP 'ffmpeg-essentials.zip'
    $extract = Join-Path $env:TEMP 'yt-dlp-ffmpeg'
    Write-Host 'FFmpeg wird heruntergeladen ...'
    Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile $archive
    if (Test-Path $extract) { Remove-Item $extract -Recurse -Force }
    Expand-Archive -Path $archive -DestinationPath $extract -Force
    $bin = Get-ChildItem $extract -Recurse -Filter ffmpeg.exe | Select-Object -First 1
    $probe = Get-ChildItem $extract -Recurse -Filter ffprobe.exe | Select-Object -First 1
    if (-not $bin -or -not $probe) { throw 'FFmpeg oder FFprobe wurde im Archiv nicht gefunden.' }
    Copy-Item $bin.FullName $ffmpeg -Force
    Copy-Item $probe.FullName $ffprobe -Force
}

if (Test-Path 'dist') { Remove-Item 'dist' -Recurse -Force }
if (Test-Path 'build') { Remove-Item 'build' -Recurse -Force }
python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name 'yt-dlp-GUI' `
    --collect-all yt_dlp `
    --add-binary 'tools\ffmpeg.exe;.' `
    --add-binary 'tools\ffprobe.exe;.' `
    gui.py
if ($LASTEXITCODE -ne 0) { throw 'Der PyInstaller-Build ist fehlgeschlagen.' }

Write-Host ''
Write-Host 'Fertig: dist\yt-dlp-GUI.exe'
