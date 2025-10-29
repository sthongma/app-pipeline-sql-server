; Inno Setup Script for SQL Server Pipeline
; This creates a professional Windows installer
; Download Inno Setup from: https://jrsoftware.org/isdl.php

#define MyAppName "SQL Server Pipeline"
#define MyAppVersion "2.2.0"
#define MyAppPublisher "Your Organization"
#define MyAppURL "https://github.com/yourusername/app-pipeline-sql-server"
#define MyAppExeName "SQLServerPipeline.exe"
#define MyAppDescription "นำเข้าข้อมูล Excel/CSV เข้า SQL Server อัตโนมัติ"

[Setup]
; App identity
AppId={{B8C9F1A2-3D4E-5F6A-7B8C-9D0E1F2A3B4C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppComments={#MyAppDescription}

; Default installation path
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}

; Output configuration
OutputDir=..\dist\installer
OutputBaseFilename=SQLServerPipeline_v{#MyAppVersion}_Setup
SetupIconFile=..\assets\icon.ico

; Compression
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
LZMANumBlockThreads=4

; Installation UI
WizardStyle=modern
WizardImageFile=compiler:WizModernImage-IS.bmp
WizardSmallImageFile=compiler:WizModernSmallImage-IS.bmp

; Privileges
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; Uninstall
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
CreateUninstallRegKey=yes
Uninstallable=yes

; Misc
DisableProgramGroupPage=yes
DisableWelcomePage=no
AllowNoIcons=yes

; Version info
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppDescription}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

; Architecture
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "thai"; MessagesFile: "compiler:Languages\Thai.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main application files from PyInstaller output
Source: "..\dist\SQLServerPipeline\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Configuration templates
Source: "..\dist\SQLServerPipeline\.env.example"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\SQLServerPipeline\README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme

; Create empty config file if not exists
Source: "..\dist\SQLServerPipeline\.env.example"; DestDir: "{app}"; DestName: ".env"; Flags: onlyifdoesntexist uninsneveruninstall

; Documentation
Source: "..\SECURITY.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\PERFORMANCE.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\CHANGELOG.md"; DestDir: "{app}\docs"; Flags: ignoreversion

; Monitoring tools (optional)
Source: "..\monitoring\*"; DestDir: "{app}\monitoring"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
; Create necessary directories
Name: "{app}\logs"; Permissions: users-modify
Name: "{app}\Uploaded_Files"; Permissions: users-modify
Name: "{app}\config"; Permissions: users-modify
Name: "{userappdata}\{#MyAppName}"; Permissions: users-modify

[Icons]
; Start Menu
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "{#MyAppDescription}"
Name: "{group}\คู่มือการใช้งาน"; Filename: "{app}\README.md"
Name: "{group}\ตั้งค่าฐานข้อมูล"; Filename: "notepad.exe"; Parameters: """{app}\.env"""; Comment: "แก้ไขการตั้งค่าฐานข้อมูล"
Name: "{group}\โฟลเดอร์โปรแกรม"; Filename: "{app}"; Comment: "เปิดโฟลเดอร์โปรแกรม"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Desktop icon
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Comment: "{#MyAppDescription}"

; Quick Launch
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; Open README after installation
Filename: "{app}\README.md"; Description: "เปิดคู่มือการใช้งาน"; Flags: postinstall shellexec skipifsilent nowait

; Open .env file for configuration
Filename: "notepad.exe"; Parameters: """{app}\.env"""; Description: "ตั้งค่าการเชื่อมต่อฐานข้อมูล"; Flags: postinstall skipifsilent nowait

; Run the application
Filename: "{app}\{#MyAppExeName}"; Description: "เปิดโปรแกรม {#MyAppName}"; Flags: postinstall skipifsilent nowait

[UninstallDelete]
; Clean up user data (optional - commented out for safety)
; Type: filesandordirs; Name: "{app}\logs"
; Type: filesandordirs; Name: "{app}\Uploaded_Files"
Type: filesandordirs; Name: "{app}\*.pyc"
Type: filesandordirs; Name: "{app}\__pycache__"

[Code]
{ Custom Pascal Script for installer }

// Check if .NET Framework is installed (if needed)
function IsDotNetInstalled: Boolean;
begin
  Result := True; // Modify if your app needs .NET
end;

// Check if SQL Server driver is available
function IsSQLServerDriverInstalled: Boolean;
var
  Names: TArrayOfString;
  I: Integer;
begin
  Result := False;
  if RegGetSubkeyNames(HKLM, 'SOFTWARE\ODBC\ODBCINST.INI', Names) then
  begin
    for I := 0 to GetArrayLength(Names) - 1 do
    begin
      if Pos('SQL Server', Names[I]) > 0 then
      begin
        Result := True;
        Break;
      end;
    end;
  end;
end;

// Custom welcome message
procedure InitializeWizard;
var
  WelcomeLabel: TNewStaticText;
begin
  // Add custom welcome text
  WelcomeLabel := TNewStaticText.Create(WizardForm);
  WelcomeLabel.Parent := WizardForm.WelcomePage;
  WelcomeLabel.Caption :=
    'โปรแกรมนำเข้าข้อมูล Excel และ CSV เข้า SQL Server' + #13#10 +
    'รองรับภาษาไทย ใช้งานง่าย ไม่ต้องเขียนโค้ด' + #13#10#13#10 +
    'ฟีเจอร์หลัก:' + #13#10 +
    '  • นำเข้าไฟล์ Excel/CSV อัตโนมัติ' + #13#10 +
    '  • ตรวจสอบและทำความสะอาดข้อมูล' + #13#10 +
    '  • รองรับภาษาไทย UTF-8' + #13#10 +
    '  • ระบบ Health Monitoring' + #13#10 +
    '  • ความปลอดภัยระดับ Enterprise';
  WelcomeLabel.AutoSize := True;
  WelcomeLabel.WordWrap := True;
  WelcomeLabel.Top := WizardForm.WelcomeLabel2.Top + WizardForm.WelcomeLabel2.Height + 20;
  WelcomeLabel.Left := WizardForm.WelcomeLabel2.Left;
  WelcomeLabel.Width := WizardForm.WelcomeLabel2.Width;
end;

// Check prerequisites before installation
function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';

  // Check for SQL Server ODBC driver
  if not IsSQLServerDriverInstalled then
  begin
    if MsgBox('ไม่พบ SQL Server ODBC Driver ในระบบ' + #13#10#13#10 +
              'โปรแกรมต้องการ ODBC Driver เพื่อเชื่อมต่อกับ SQL Server' + #13#10 +
              'คุณต้องการดาวน์โหลดและติดตั้งหรือไม่?',
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      ShellExec('open',
                'https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server',
                '', '', SW_SHOW, ewNoWait, nil);
      Result := 'กรุณาติดตั้ง SQL Server ODBC Driver ก่อนดำเนินการต่อ';
    end;
  end;
end;

// Post-installation message
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Create a simple batch file for easy updates
    SaveStringToFile(ExpandConstant('{app}\update_config.bat'),
                    '@echo off' + #13#10 +
                    'notepad.exe .env' + #13#10 +
                    'pause', False);
  end;
end;

// Uninstall confirmation
function InitializeUninstall(): Boolean;
begin
  Result := True;
  if MsgBox('คุณต้องการถอนการติดตั้ง SQL Server Pipeline หรือไม่?' + #13#10#13#10 +
            'หมายเหตุ: ไฟล์ config และ logs จะไม่ถูกลบ',
            mbConfirmation, MB_YESNO) = IDNO then
  begin
    Result := False;
  end;
end;
