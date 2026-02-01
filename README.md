# quick log

minimalist tray app for taking notes fast. built for teachers who need to log things during class without anyone seeing.

## what it does
three modes you can cycle through:
- **todo**: basic checkbox list. yellow icon when you have things to do, green when done.
- **notes**: simple text notes. yellow icon.
- **stealth (marks)**: password-style input. red icon with a dot. logs are hidden in a submenu. perfect for logging behavior marks while the projector is on.

## controls
- **left click tray**: toggle between modes.
- **right click tray**: see your logs / add new stuff.
- **| (pipe key)**: open the floating input bar instantly.
- **alt + |**: switch to next mode.
- **enter**: save.
- **esc / click away**: cancel.

## how to get it
1. **use the release**: go to the releases page and download `QuickLog.exe`.
2. **build it yourself**:
   - install `uv`
   - run `uv sync`
   - run `uv run pyinstaller --noconsole --onefile --name "QuickLog" main.py`
   - find it in `dist/QuickLog.exe`

## add to startup
to make it start when your computer turns on:
- run `setup_startup.bat` (it will create a shortcut in your windows startup folder)
- or just manually put a shortcut of the exe in `shell:startup`
