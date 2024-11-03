echo off
:title
title YouTube Video Downloader
color 0A

:: Large title section
echo ==================================================
echo             YOUTUBE VIDEO DOWNLOADER
echo ==================================================
echo                   by kokolino75
echo.       (Plugin for yt-dlp created by kokolino75)
echo ==================================================
echo.

:start
:: Change color for user prompts - yellow color
color 0E
set /p filename="Enter the desired file name (default is 'video_output'): "
if "%filename%"=="" set filename=video_output

echo.
set /p url="Enter the video URL: "
if "%url%"=="" (
    color 0C
    echo ERROR: No URL provided. Please enter a valid URL.
    echo.
    goto start
)

:: Change color for download start message - light green color
color 0A
echo Downloading video...

:: Attempt to download video
yt-dlp -f bestvideo+bestaudio --merge-output-format mp4 -o "G:\YOTUBE DOUNLOAD MOI\%filename%.mp4" %url%
if errorlevel 1 (
    color 0C
    echo.
    echo ==================================================
    echo           ERROR: An error occurred during download.
    echo           Please check the URL and try again.
    echo ==================================================
    echo.
    goto start
)

:: Change color for completion message - blue color
color 09
echo.
echo ==================================================
echo         Download completed! Saved as: %filename%.mp4
echo ==================================================
pause
