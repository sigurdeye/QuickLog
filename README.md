# QuickLog

A dead-simple, minimalist capture tool for your Windows system tray. QuickLog stays out of your way until you need to jot something down, log a thought, or track a quick task.

## Features

- **Minimalist UI**: yeah
- **Three Modes**:
  - **Todo**: Quick task tracking.
  - **Note**: Fast text capture with one-click copy.
  - **Log (Mark)**: Timestamped entries for logging anything your day.
- **Few Distraction**: It's just a tray icon and a floating input bar.
- **Low customizability**: I'm not good at programming

## Hotkeys (Default)

- **Alt + q**: Open the floating input bar instantly.
- **Ctrl + q**: Switch between modes (Todo, Note, Log).
- **Escape**: Close the input bar without saving. You can also just click outside the bar to close it.

## Configuration

Right click the tray icon and click `settings` to configure stuff. Here you can:
- Enable/Disable specific modes.
- Toggle masked input mode for any mode to keep your inputs private (they turn into asterisks as you type). Great if you're connected to a projector.

## Installation & Setup

### For Users
1. Download `QuickLog.exe` from the Releases page here on GitHub.
2. Run the executable. It will appear in your system tray.
3. Right click the tray icon for QuickLog, go to settings, and click "Run at startup" to make the app do just that. After adding it to startup, you can remove it from startup by clicking "Remove from startup" instead.

### For Developers (using `uv`)
1. Clone the repository:
   ```bash
   git clone https://github.com/sigurdeye/QuickLog.git
   cd QuickLog
   ```
2. Install dependencies and run:
   ```bash
   uv sync
   uv run python main.py
   ```

## Building from source
To create your own standalone executable:
```bash
uv run pyinstaller QuickLog.spec --noconfirm
```

## License
MIT

## Technical Details
- **Binary Size**: ~19 MB (standalone executable).
- **System Impact**: Extremely low. The app uses minimal RAM and CPU, and the startup impact is negligible as it simply waits for your input bar shortcut.
- **Storage**: All data (todos, notes, logs) and settings are stored locally in `%USERPROFILE%\.quicklog.json`. This is a simple human-readable text file that stays on your machine.

## Future Plans
- Custom shortcut key support (configure your own bindings for opening the bar and cycling modes).

---

[![Buy Me A Coffee](https://img.shields.io/badge/Feel%20free%20to%20support%20me-☕%20buymeacoffee.com-FFDD00?style=for-the-badge&logoColor=black)](https://www.buymeacoffee.com/sigurdeye)
