# Quick Log

Minimalist tray app for taking notes fast. Built for teachers who need a discreet way to log behavior and marks during class.

## What it does
Three modes you can cycle through:
- **Todo**: Basic checkbox list. Icon is yellow when you have tasks, and turns green when all tasks are done.
- **Notes**: Standard text notes for quick reminders.
- **Marks (stealthed)**: This is the hidden mode. It uses password-style input so students can't see the text of what you are writing. Logs are also hidden in a submenu. Perfect for logging behavior marks while the projector is on.

## Controls
- **Left click tray**: Toggle between modes.
- **Right click tray**: See your logs / add new stuff.
- **| (pipe key)**: Open the floating input bar instantly.
- **Alt + |**: Switch to next mode.
- **Enter**: Save.
- **Esc / Click away**: Cancel.

## How to get it
Choose one of these two options:

### Option A: Use the release
Go to the releases page and download `QuickLog.exe`. This is the easiest way.

### Option B: Build it yourself
- Install `uv`.
- Run `uv sync`.
- Run `uv run pyinstaller --noconsole --onefile --name "QuickLog" main.py`.
- Find your file in `dist/QuickLog.exe`.

## Add to startup
To make it start when your computer turns on:
- Run `setup_startup.bat` (it will create a shortcut in your windows startup folder).
- Or just manually put a shortcut of the exe in `shell:startup`.
