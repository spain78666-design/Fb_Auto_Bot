; ==============================================================================
; FB Auto Bot - Inno Setup Script
; Creates a professional Windows Setup Wizard (FBAutoBot_Setup_v5.0.exe)
; Installs into: {localappdata}\Programs\FBAutoBot (No Admin UAC popup needed)
; ==============================================================================

#define MyAppName "FB Auto Bot"
#define MyAppVersion "5.0.0"
#define MyAppPublisher "FB Auto Bot Enterprise"
#define MyAppURL "https://fbautobot.vercel.app/"
#define MyAppExeName "FBAutoBot.exe"
#define MyAppID "fbautobot.enterprise.automation.v24"

[Setup]
; Unique AppId generated for FB Auto Bot
AppId={{E8B7F92A-4D31-4A56-B1C8-92F73DAE84B0}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\FBAutoBot
DisableProgramGroupPage=yes
DefaultGroupName={#MyAppName}
OutputDir=dist_installer
OutputBaseFilename=FBAutoBot_Setup_v5.0
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
DisableDirPage=no
DisableReadyPage=no
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=assets\logo.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main Executable & Compiled Application Directory
; Note: Run PyInstaller first so 'dist\FBAutoBot' exists
Source: "dist\FBAutoBot\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Preserve user's local config and accounts during updates
[Dirs]
Name: "{app}\config"; Flags: uninsneveruninstall
Name: "{app}\profiles"; Flags: uninsneveruninstall
Name: "{app}\temp_uploads"; Flags: deleteafterinstall

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; IconIndex: 0; AppUserModelID: "{#MyAppID}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; IconIndex: 0; AppUserModelID: "{#MyAppID}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
