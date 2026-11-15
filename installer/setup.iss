; Inno Setup Skript fuer R3E Karriere
; Baut aus dist\R3EKarriere\ einen Windows-Installer.
; Version kommt aus der Umgebungsvariable APP_VERSION (in CI aus dem Git-Tag).
#define AppName "R3E Karriere"
#ifndef AppVer
  #define AppVer GetEnv("APP_VERSION")
#endif
#if AppVer == ""
  #define AppVer "0.0.0"
#endif

[Setup]
AppName={#AppName}
AppVersion={#AppVer}
AppPublisher=Pfoetiman76
SetupIconFile={#SourcePath}\..\assets\icon.ico
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
UninstallDisplayName={#AppName} {#AppVer}
OutputDir=Output
OutputBaseFilename=R3E-Karriere-Setup-{#AppVer}
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\R3EKarriere.exe

[Languages]
Name: "de"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknuepfung erstellen"; GroupDescription: "Zusaetzliche Symbole:"

[Files]
Source: "..\dist\R3EKarriere\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\R3EKarriere.exe"
Name: "{group}\{#AppName} deinstallieren"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\R3EKarriere.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\R3EKarriere.exe"; Description: "{#AppName} starten"; Flags: nowait postinstall skipifsilent
