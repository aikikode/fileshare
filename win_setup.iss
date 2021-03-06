; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

#define MyAppName "Fileshare"
#define MyAppVersion "0.5.1"
#define MyAppPublisher "Denis Kovalev"
#define MyAppURL "http://aikikode.github.io/fileshare/"
#define MyAppExeName "indicator-fileshare.pyw"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{24B96920-94AD-48B2-B5A0-411629736A1C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
;AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={pf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
InfoBeforeFile=README
OutputBaseFilename=fileshare_setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "startup";     Description: "Automatically start on login"; GroupDescription: "{cm:AdditionalIcons}"
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}";       GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "indicator-fileshare"; DestDir: "{app}"; DestName: indicator-fileshare.pyw; Flags: ignoreversion
Source: "AUTHORS"; DestDir: "{app}"; Flags: ignoreversion
Source: "CHANGELOG"; DestDir: "{app}"; Flags: ignoreversion
Source: "grabbers.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "INSTALL"; DestDir: "{app}"; Flags: ignoreversion
Source: "README"; DestDir: "{app}"; Flags: ignoreversion
Source: "upload_services.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "icons\*"; DestDir: "{app}\icons\"; Flags: ignoreversion
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{commonstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: shellexec postinstall skipifsilent

