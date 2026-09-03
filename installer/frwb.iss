; Installer for the File Rename Processing Workbench. Built with Inno Setup 6:
;
;     ISCC.exe installer\frwb.iss
;
; It expects dist\FRWB\ to exist - run tools\buildExe.py first. The version is
; passed in by tools\buildInstaller.py so that it can never disagree with
; appConfig; the default below is only what a bare ISCC run would use.
;
; Per-user by design. This tool renames files a person owns, in folders they
; already have; it needs nothing machine-wide, and asking for administrator
; rights to install a file renamer is how a small tool becomes a thing IT has
; to approve.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#define AppName "File Rename Processing Workbench"
#define ShortName "FRWB"
#define Publisher "Charette AI Group, LLC"
#define AppUrl "https://github.com/Charette-AI-Group/FRWB"
#define ExeName "FRWB.exe"
#define BundleDir "..\dist\FRWB"

[Setup]
; Fixed for the life of the application: this is what lets an upgrade replace
; an install rather than sit beside it, and what the uninstaller is found by.
AppId={{7F3C1A94-5E2D-4B86-9C11-2A6D8F4E0B37}
AppName={#AppName}
AppVersion={#AppVersion}
VersionInfoVersion={#AppVersion}
AppPublisher={#Publisher}
AppPublisherURL={#AppUrl}
AppSupportURL={#AppUrl}
AppUpdatesURL={#AppUrl}/releases
DefaultDirName={autopf}\{#ShortName}
DefaultGroupName={#ShortName}
DisableProgramGroupPage=yes
SetupIconFile=..\src\frwb\resources\frwb.ico
UninstallDisplayIcon={app}\{#ExeName}
UninstallDisplayName={#AppName}
OutputDir=..\dist
OutputBaseFilename=frwbSetup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Per-user, so there is no UAC prompt and no Program Files. The application
; writes only to APPDATA, so nothing here needs more than the user has.
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Shown on the first page, so the licence is read before anything is written.
LicenseFile=..\LICENSE

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#ShortName}"; Filename: "{app}\{#ExeName}"
Name: "{group}\Uninstall {#ShortName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#ShortName}"; Filename: "{app}\{#ExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#ExeName}"; Description: "Start {#ShortName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; The bundle only. Deliberately not the settings under APPDATA: an uninstall
; that silently discards somebody's saved folder and rename settings is a
; surprise, and a reinstall is the commonest reason to uninstall.
Type: filesandordirs; Name: "{app}\_internal"

[Code]
{ A running copy holds its own files open, so replacing them mid-upgrade
  fails with a message about a file in use that says nothing about why. Ask
  first instead, in words that name the application. }
function InitializeSetup(): Boolean;
var
  WindowHandle: HWND;
begin
  Result := True;
  WindowHandle := FindWindowByWindowName('{#ShortName} - {#AppName}');
  if WindowHandle <> 0 then
    Result := MsgBox(
      '{#ShortName} appears to be running.' + #13#10#13#10 +
      'Close it before continuing, or setup cannot replace its files.' + #13#10#13#10 +
      'Continue anyway?',
      mbConfirmation, MB_YESNO) = IDYES;
end;
