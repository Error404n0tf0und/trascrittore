; Installatore di Trascrittore - by Error404.ntf
; Da compilare con Inno Setup (https://jrsoftware.org/isdl.php): apri questo file e premi Compile.
; Il risultato e' Output\Trascrittore-Setup.exe

#define MyAppName "Trascrittore"
#define MyAppVersion "1.0"
#define MyAppPublisher "Error404.ntf"

[Setup]
AppId={{D9F8D9B6-C37E-45C6-8316-406C668C442A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Registra e trascrive audio in locale
; installazione per l'utente corrente: niente permessi di amministratore e cartella scrivibile
; (il programma salva li' i modelli scaricati)
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\Trascrittore
DisableProgramGroupPage=yes
DisableDirPage=yes
OutputDir=Output
OutputBaseFilename=Trascrittore-Setup
SetupIconFile=..\app\app.ico
UninstallDisplayIcon={app}\app.ico
UninstallDisplayName={#MyAppName}
WizardStyle=modern
Compression=lzma2
SolidCompression=yes

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\app\*"; DestDir: "{app}"; Excludes: "INSTALLA.bat,avvia.bat,__pycache__,modelli,registrazioni,errori.txt,*.vbs"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\avvia.vbs"""; WorkingDir: "{app}"; IconFilename: "{app}\app.ico"; Comment: "Trascrittore - by {#MyAppPublisher}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\avvia.vbs"""; WorkingDir: "{app}"; IconFilename: "{app}\app.ico"; Comment: "Trascrittore - by {#MyAppPublisher}"; Tasks: desktopicon

[Run]
Filename: "{sys}\wscript.exe"; Parameters: """{app}\avvia.vbs"""; Description: "Avvia Trascrittore"; Flags: postinstall nowait skipifsilent

[UninstallDelete]
; via i modelli scaricati (1,6 GB) e i file temporanei.
; Le registrazioni in Documenti\Trascrittore NON vengono toccate.
Type: filesandordirs; Name: "{app}\modelli"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: files; Name: "{app}\avvia.vbs"
Type: files; Name: "{app}\errori.txt"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    WizardForm.StatusLabel.Caption := 'Installo Python e i componenti: puo'' richiedere qualche minuto...';
    if not Exec(ExpandConstant('{app}\setup_ambiente.bat'), '', ExpandConstant('{app}'),
                SW_SHOW, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
      MsgBox('Non sono riuscito a preparare tutti i componenti.' + #13#10 +
             'Controlla la connessione a internet e lancia di nuovo l''installazione.',
             mbError, MB_OK);
  end;
end;
