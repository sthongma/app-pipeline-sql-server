; Inno Setup Script for SQL Server Data Pipeline
; This script creates a professional Windows installer

[Setup]
; Application Information
AppName=SQL Server Data Pipeline
AppVersion=0.1.1
AppPublisher=PIPELINE_SQLSERVER Development Team
AppPublisherURL=https://github.com/sthongma/app-pipeline-sql-server
AppSupportURL=https://github.com/sthongma/app-pipeline-sql-server/issues
AppUpdatesURL=https://github.com/sthongma/app-pipeline-sql-server/releases

; Installation Directories
DefaultDirName={autopf}\SQL Server Pipeline
DefaultGroupName=SQL Server Pipeline
DisableProgramGroupPage=yes

; Output Configuration
OutputDir=..\installer_output
OutputBaseFilename=SQLServerPipeline_v0.1.1_Setup
Compression=lzma2/max
SolidCompression=yes

; Icons and Visuals
SetupIconFile=app_icon.ico
UninstallDisplayIcon={app}\SQLServerPipeline.exe
WizardStyle=modern

; Architecture and Permissions
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin

; License
LicenseFile=..\LICENSE

; Uninstall
UninstallDisplayName=SQL Server Data Pipeline

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"
Name: "quicklaunchicon"; Description: "Create a &Quick Launch icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
; Main executable
Source: "..\dist\SQLServerPipeline.exe"; DestDir: "{app}"; Flags: ignoreversion

; Documentation
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

; Environment file template - save to config directory
Source: "..\.env.example"; DestDir: "{app}\config"; DestName: ".env"; Flags: onlyifdoesntexist uninsneveruninstall

; Configuration files (create empty if doesn't exist)
Source: "..\config\app_settings.json"; DestDir: "{app}\config"; Flags: ignoreversion onlyifdoesntexist

[Dirs]
; Create necessary directories with write permissions
Name: "{app}"; Permissions: users-modify
Name: "{app}\config"; Permissions: users-modify
Name: "{app}\temp"; Permissions: users-modify

[Icons]
; Start Menu shortcuts
Name: "{group}\SQL Server Pipeline"; Filename: "{app}\SQLServerPipeline.exe"; Comment: "Launch SQL Server Data Pipeline"
Name: "{group}\Uninstall SQL Server Pipeline"; Filename: "{uninstallexe}"

; Desktop shortcut (optional)
Name: "{autodesktop}\SQL Server Pipeline"; Filename: "{app}\SQLServerPipeline.exe"; Tasks: desktopicon; Comment: "Launch SQL Server Data Pipeline"

; Quick Launch (optional)
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\SQL Server Pipeline"; Filename: "{app}\SQLServerPipeline.exe"; Tasks: quicklaunchicon

[Run]
; Open README after installation
Filename: "{app}\README.md"; Description: "View README file"; Flags: postinstall shellexec skipifsilent nowait unchecked

; Launch application after installation
Filename: "{app}\SQLServerPipeline.exe"; Description: "Launch SQL Server Pipeline"; Flags: nowait postinstall skipifsilent

[Code]
// Custom code for installation
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Show important information
    MsgBox('Important: Please configure your database connection in the .env file before running the application.' + #13#10 + #13#10 +
           'You will also need ODBC Driver 17 or 18 for SQL Server installed.' + #13#10 +
           'Download: https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server',
           mbInformation, MB_OK);
  end;
end;
