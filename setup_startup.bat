@echo off
set "targetDir=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "exeName=QuickLog.exe"
set "shortcutName=QuickLog.lnk"
set "exePath=%~dp0dist\%exeName%"

if not exist "%exePath%" (
    echo [!] QuickLog.exe not found in dist folder.
    echo [!] please build the exe first or place it in the dist folder.
    pause
    exit /b
)

echo [*] creating startup shortcut for Quick Log...
powershell "$s=(New-Object -COM WScript.Shell).CreateShortcut('%targetDir%\%shortcutName%');$s.TargetPath='%exePath%';$s.WorkingDirectory='%~dp0dist';$s.Save()"

echo [!] done. quick log will now start with windows.
pause
