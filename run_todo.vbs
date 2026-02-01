Set WshShell = CreateObject("WScript.Shell")
' Get the current directory of the script
strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
' Run the app using the virtual environment's pythonw.exe (which has no console window)
WshShell.Run """" & strPath & "\.venv\Scripts\pythonw.exe"" """ & strPath & "\main.py""", 0, False
Set WshShell = Nothing
