; SecureVault Installer
; Inno Setup 6 script
; Produces: installer\output\SecureVaultSetup.exe

#define AppName      "SecureVault"
#define AppVersion   "1.0.2"
#define AppPublisher "Hossain Abedy"
#define AppURL       "https://www.hossainabedy.com/policies/securevault/support-policy.html"
#define HostName     "com.securevault.nativehost"
#define FFExtID      "securevault@abedy"

[Setup]
AppId={{8A3F2E1D-4B6C-4D9A-8E2F-1C3A5B7D9E0F}}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=output
OutputBaseFilename=SecureVaultSetup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\SecureVault.exe
CloseApplications=yes
RestartApplications=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=assets\logo.ico
WizardImageFile=assets\banner.bmp

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"
Name: "startupicon"; Description: "Start SecureVault with Windows"; Flags: unchecked

; ── Files ────────────────────────────────────────────────────────────────────

[Files]
; Main application (PyInstaller onedir output)
Source: "dist\SecureVault\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Native host executable
Source: "dist\native_host.exe"; DestDir: "{app}\native_host"; Flags: ignoreversion
Source: "dist\com.securevault.nativehost.json"; DestDir: "{app}\native_host"; Flags: ignoreversion
Source: "dist\com.securevault.nativehost.firefox.json"; DestDir: "{app}\native_host"; DestName: "com.securevault.nativehost.firefox.json"; Flags: ignoreversion

; Browser extensions (unpacked — for Chrome/Edge load-unpacked)
Source: "..\browser_extension\*"; DestDir: "{app}\browser_extension"; Flags: ignoreversion recursesubdirs createallsubdirs

; Firefox extension (.xpi)
Source: "dist\securevault_firefox.xpi"; DestDir: "{app}"; Flags: ignoreversion

; Setup guide HTML
Source: "assets\setup.html"; DestDir: "{app}"; DestName: "SETUP.html"; Flags: ignoreversion

; Setup logo
Source: "assets\logo.ico"; DestDir: "{app}"; Flags: ignoreversion

; ── Registry — Native Host ────────────────────────────────────────────────────

[Registry]

; Chrome
Root: HKCU; Subkey: "Software\Google\Chrome\NativeMessagingHosts\{#HostName}"; \
    ValueType: string; ValueName: ""; \
    ValueData: "{app}\native_host\com.securevault.nativehost.json"; \
    Flags: uninsdeletekey

; Microsoft Edge
Root: HKCU; Subkey: "Software\Microsoft\Edge\NativeMessagingHosts\{#HostName}"; \
    ValueType: string; ValueName: ""; \
    ValueData: "{app}\native_host\com.securevault.nativehost.json"; \
    Flags: uninsdeletekey

; Firefox
Root: HKCU; Subkey: "Software\Mozilla\NativeMessagingHosts\{#HostName}"; \
    ValueType: string; ValueName: ""; \
    ValueData: "{app}\native_host\com.securevault.nativehost.firefox.json"; \
    Flags: uninsdeletekey

; Start with Windows (optional)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "{#AppName}"; \
    ValueData: """{app}\SecureVault.exe"""; \
    Flags: uninsdeletevalue; Tasks: startupicon

; ── Shortcuts ─────────────────────────────────────────────────────────────────

[Icons]
Name: "{group}\{#AppName}";          Filename: "{app}\SecureVault.exe"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\SecureVault.exe"; IconFilename: "{app}\SecureVault.exe"; Tasks: desktopicon

; ── Post-install actions ──────────────────────────────────────────────────────

[Run]
; Open Chrome extension setup guide after install
Filename: "{app}\setup.html"; \
    Description: "Open browser extension setup guide"; \
    Flags: postinstall shellexec skipifsilent; \
    StatusMsg: "Opening setup guide..."

; Launch SecureVault after install
Filename: "{app}\SecureVault.exe"; \
    Description: "Launch {#AppName} now"; \
    Flags: postinstall nowait skipifsilent

; ── Pascal script — creates manifests and Firefox policy ─────────────────────

[Code]

function GetFirefoxInstallDir(): string;
  var
    ExePath: string;
  begin
    Result := '';

    // 64-bit registry
    if RegQueryStringValue(
        HKLM,
        'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\firefox.exe',
        '',
        ExePath) then
    begin
      Result := ExtractFileDir(ExePath);
      Exit;
    end;

    // 32-bit registry
    if RegQueryStringValue(
        HKLM32,
        'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\firefox.exe',
        '',
        ExePath) then
    begin
      Result := ExtractFileDir(ExePath);
      Exit;
    end;

    // Fallback locations
    if DirExists(ExpandConstant('{pf}\Mozilla Firefox')) then
      Result := ExpandConstant('{pf}\Mozilla Firefox')
    else if DirExists(ExpandConstant('{pf32}\Mozilla Firefox')) then
      Result := ExpandConstant('{pf32}\Mozilla Firefox');
  end;

procedure InstallFirefoxEnterprisePolicy();
var
  PolicyDir:     string;
  PolicyContent: string;
  XpiPath:       string;
  SafeXpiPath:   string;
begin
  // Firefox enterprise policy — auto-installs extension permanently
  PolicyDir := GetFirefoxInstallDir();

  if PolicyDir = '' then
  begin
      Log('Firefox installation not found. Skipping Firefox enterprise policy.');
      Exit;
  end;

  PolicyDir := PolicyDir + '\distribution';

  XpiPath := ExpandConstant('{app}\securevault_firefox.xpi');
  // Firefox policy needs forward slashes for file:/// URL
  StringChangeEx(XpiPath, '\', '/', True);
  SafeXpiPath := 'file:///' + XpiPath;

  PolicyContent :=
    '{' + #13#10 +
    '  "policies": {' + #13#10 +
    '    "ExtensionSettings": {' + #13#10 +
    '      "{#FFExtID}": {' + #13#10 +
    '        "installation_mode": "force_installed",' + #13#10 +
    '        "install_url": "' + SafeXpiPath + '"' + #13#10 +
    '      }' + #13#10 +
    '    }' + #13#10 +
    '  }' + #13#10 +
    '}';

ForceDirectories(PolicyDir);

SaveStringToFile(
    PolicyDir + '\policies.json',
    PolicyContent,
    False
);

end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
    if CurStep = ssPostInstall then
    begin
        InstallFirefoxEnterprisePolicy();
        Log('Firefox enterprise policy installed.');
    end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  PolicyFile: string;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if GetFirefoxInstallDir() <> '' then
    begin
      PolicyFile := GetFirefoxInstallDir() + '\distribution\policies.json';

      if FileExists(PolicyFile) then
        DeleteFile(PolicyFile);
    end;
  end;
end;
