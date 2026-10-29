; Installatore Windows (Inno Setup). Viene compilato da GitHub Actions:
;   iscc /DAppVersion=1.0.0 packaging\gestionale.iss
; Installa nella cartella utente (non servono permessi di amministratore)
; e NON tocca mai i dati: il database sta in %LOCALAPPDATA%\Gestionale.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppName "Gestionale"

[Setup]
AppId={{6B1C2E7A-3F4D-4C1B-9E2A-7D5F0A9C8B31}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppName}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=Gestionale-Setup-{#AppVersion}
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\Gestionale.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; Description: "Crea un'icona sul desktop"; GroupDescription: "Icone:"

[Files]
; la cartella creata da PyInstaller (--onedir)
Source: "..\dist\Gestionale\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; rimuove i file della versione precedente prima di copiare quella nuova
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\Gestionale.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\Gestionale.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Gestionale.exe"; Description: "Avvia {#AppName}"; Flags: nowait postinstall skipifsilent
