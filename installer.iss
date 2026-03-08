[Setup]
AppName=yt-dlp Desktop (Inginitty)
AppVersion=1.0
AppPublisher=cerits
AppPublisherURL=https://github.com/yt-dlp/yt-dlp
DefaultDirName={autopf}\yt-dlp-Desktop
DefaultGroupName=yt-dlp Desktop
OutputDir=dist
OutputBaseFilename=yt-dlp-Desktop-Setup
SetupIconFile=app\static\logo.ico
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\yt-dlp-Desktop.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "app\static\logo.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\yt-dlp Desktop"; Filename: "{app}\yt-dlp-Desktop.exe"; IconFilename: "{app}\logo.ico"
Name: "{autodesktop}\yt-dlp Desktop"; Filename: "{app}\yt-dlp-Desktop.exe"; IconFilename: "{app}\logo.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\yt-dlp-Desktop.exe"; Description: "{cm:LaunchProgram,yt-dlp Desktop}"; Flags: nowait postinstall skipifsilent
