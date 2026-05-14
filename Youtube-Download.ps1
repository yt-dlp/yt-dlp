<#
    Youtube-Download.ps1
    For downloading YT vids in either video or audio format; a wrapper for the yt-dlp.exe binary
    Default format is MP4 (video), or MP3 if -audio is passed
    Supports playlist downloads and organizes files accordingly
    Logs each download to youtube-download.log
#>

[CmdletBinding()]
param
(
    [Parameter(Mandatory=$false)][string]$url,  # YT vid URL
    [Parameter(Mandatory=$false)][string]$dest = "$env:USERPROFILE\Videos",  # Download destination path
    [Parameter(Mandatory=$false)][switch]$audio,  # Audio only?
    [Parameter(Mandatory=$false)][switch]$update,  # Update yt-dlp binary?
    [Parameter(Mandatory=$true)][string]$configPath
)

try
{
    $config = Get-Content -Path $configPath | ConvertFrom-Json -AsHashtable

    $config.logFile = [Environment]::ExpandEnvironmentVariables($config.logFile)
    $config.jsruntimePath = [Environment]::ExpandEnvironmentVariables($config.jsruntimePath)
}
catch
{
    Write-Error "Error loading config file: $_"

    Exit 1
}

try
{Start-Transcript -Path $config.logFile}
catch
{Write-Warning "Transcript could not be started: $_"}

if (-not (Test-Path -Path $dest))
{
    try
    {
        New-Item -ItemType Directory -Path $dest -Force | Out-Null

        Write-Warning "Created missing destination directory: $dest"
    }
    catch
    {
        Write-Error "Failed to create destination directory: $dest"

        Exit 1
    }
}

$binaryPath = $config.binaryPath
$ffmpegPath = $config.ffmpegPath
$jsruntime = "$($config.jsruntimeName):$($config.jsruntimePath)"
$videoSettings = $config.videoSettings
$audioSettings = $config.audioSettings

function Update-Binary
{
    [CmdletBinding()]
    param ([Parameter(Mandatory=$false)][string]$path = $binaryPath)

    begin
    {
        Write-Host "Updating yt-dlp binary at $path..." -ForegroundColor Cyan
    }
    process
    {
        & $path "-U"
    }
    end
    {
        if ($LASTEXITCODE -eq 0)
        {
            Write-Host "| Update successful!" -ForegroundColor Green
        }
        else
        {
            Write-Warning "| Update failed!  Please try manually downloading the latest binary..."
        }
    }
}

# Determine if the URL is a playlist
$usingPlaylistStructure = $url -match "list="

# Choose output template based on content type
$outputTemplate = $($usingPlaylistStructure ? "$dest\%(playlist_title)s\%(playlist_index)s - %(title)s.%(ext)s" : "$dest\%(title)s.%(ext)s")

# Build argument list
$dlArgs = @($url, "-o", $outputTemplate, "--ffmpeg-location", $ffmpegPath, "--js-runtimes", $jsruntime)

if ($audio.IsPresent)
{
    $dlArgs += @(
        "-x",
        "--audio-format", $audioSettings
    )
}
else
{
    $dlArgs += @(
        "-f",
        $videoSettings
    )
}

if ($update.IsPresent)
{
    Update-Binary
}

if ($PSBoundParameters.Debug.IsPresent)
{
    Write-Host
    Write-Debug "Running command: $binaryPath $($dlArgs -join ' ')"
    Write-Host
}
else
{Write-Host}

try
{
    if ($url)
    {
        & $binaryPath @dlArgs
    
        if ($LASTEXITCODE -eq 0)
        {
            Write-Host -ForegroundColor Green "`n|> YT-$(($audio.IsPresent) ? "audio" : "video") download complete!`n`n|> Download sent to: $dest"

            Get-ChildItem $dest | Sort-Object -Property CreationTime -Descending | Select-Object -First 1

            Write-Host
        }
        else
        {
            # Check if we've already tried updating in this specific session
            if ($env:YT_RETRY_ATTEMPT -eq "true")
            {
                Write-Error "Download failed even after update. Check the URL or logs."

                Exit 1
            }

            Write-Warning "Problem downloading $(($audio.IsPresent) ? "audio" : "video")!  Attempting to update yt-dlp..."

            Update-Binary

            # Set an Environment Variable so the child process knows we already tried
            $env:YT_RETRY_ATTEMPT = "true"

            try
            {Stop-Transcript}
            catch
            {Write-Warning "Transcript could not be stopped cleanly: $_"}

            Write-Warning "Restarting script to resume download..."

            & $PSCommandPath @PSBoundParameters

            $env:YT_RETRY_ATTEMPT = $null
            Exit $LASTEXITCODE
        }
    }
}
catch
{
    Write-Error $_

    Exit 1
}

try
{Stop-Transcript}
catch
{Write-Warning "Transcript could not be stopped cleanly: $_"}

Exit 0
