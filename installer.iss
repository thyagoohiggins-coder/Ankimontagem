; Instalador do Montador de Flashcards (Inno Setup 6)
#ifndef AppVersion
  #define AppVersion "2.2.0"
#endif

[Setup]
AppId={{7C1E4A52-3B8D-4F0A-9C55-0ABAB5F1A5C2}
AppName=Montador de Flashcards
AppVersion={#AppVersion}
AppPublisher=Montador de Flashcards
DefaultDirName={autopf}\Montador de Flashcards
DefaultGroupName=Montador de Flashcards
UninstallDisplayIcon={app}\MontadorDeFlashcards.exe
OutputDir=dist
OutputBaseFilename=MontadorDeFlashcards-Setup-{#AppVersion}
SetupIconFile=build\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\MontadorDeFlashcards\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Montador de Flashcards"; Filename: "{app}\MontadorDeFlashcards.exe"
Name: "{autodesktop}\Montador de Flashcards"; Filename: "{app}\MontadorDeFlashcards.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\MontadorDeFlashcards.exe"; Description: "{cm:LaunchProgram,Montador de Flashcards}"; Flags: nowait postinstall skipifsilent
