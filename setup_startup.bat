@echo off
set "targetDir=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "exeName=QuickLog.exe"
set "shortcutName=QuickLog.lnk"

:: Check if the exe is in the same folder as this script (Release mode)
set "exePath=%~dp0%exeName%"
set "workDir=%~dp0"

:: If not found, check the dist folder (Build mode)
if not exist "%exePath%" (
    set "exePath=%~dp0dist\%exeName%"
    set "workDir=%~dp0dist"
)

if not exist "%exePath%" (
    echo [!] QuickLog.exe not found.
    echo [!] Please place this .bat file in the same folder as QuickLog.exe
    pause
    exit /b
)

echo [*] creating startup shortcut for Quick Log...
powershell "$s=(New-Object -COM WScript.Shell).CreateShortcut('%targetDir%\%shortcutName%');$s.TargetPath='%exePath%';$s.WorkingDirectory='%workDir%';$s.Save()"

echo [!] done. quick log will now start with windows.
pause
