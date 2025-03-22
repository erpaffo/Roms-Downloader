; Script di installazione per ROMsDownloader

[Setup]
; Nome del programma e versione
AppName=ROMsDownloader
AppVersion=1.0
; Nome del file eseguibile principale (deve essere uguale a quello generato da PyInstaller)
DefaultDirName={pf}\ROMsDownloader
DefaultGroupName=ROMsDownloader
OutputBaseFilename=ROMsDownloaderInstaller
Compression=lzma
SolidCompression=yes
; Nessuna console
DisableProgramGroupPage=yes

[Files]
; Copia l'eseguibile generato nella cartella dist
Source: "dist\ROMsDownloader.exe"; DestDir: "{app}"; Flags: ignoreversion

; Se hai altre risorse (icone, file di configurazione, ecc.) aggiungile qui
; Esempio:
; Source: "path\to\config.ini"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\ROMsDownloader"; Filename: "{app}\ROMsDownloader.exe"
Name: "{commondesktop}\ROMsDownloader"; Filename: "{app}\ROMsDownloader.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crea un collegamento sul desktop"; GroupDescription: "Opzioni aggiuntive:"; Flags: unchecked
