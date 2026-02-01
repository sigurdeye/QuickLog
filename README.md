# QuickLog

A dead-simple, minimalist capture tool for your Windows system tray. QuickLog stays out of your way until you need to jot something down, log a thought, or track a quick task.

## Features

- **Minimalist UI**: A "glassy" dark-themed input bar that appears only when you need it.
- **Three Modes**:
  - **Todo**: Quick task tracking.
  - **Note**: Fast text capture with one-click copy.
  - **Log (Mark)**: Timestamped entries for logging your day.
- **Zero Distraction**: No buttons, no menus, no noise. Just your thoughts.
- **Hidden Settings**: Type `settings` in the input bar to unlock customization.
- **Global Hotkeys**: Custom system-wide shortcuts.
- **Sleep-Aware**: Automatically re-registers hotkeys after your laptop wakes up.

## Hotkeys (Default)

- **Alt + |**: Open the floating input bar instantly.
- **Ctrl + |**: Switch between modes (Todo, Note, Log).
- **Escape**: Close the input bar without saving.

## Configuration

Type `settings` (case-insensitive) into the input bar to open the configuration menu. Here you can:
- Enable/Disable specific modes.
- Toggle "Password Mode" (asterisks) for any mode to keep your inputs private.

## Installation & Setup

### For Users
1. Download `QuickLog.exe` from the [Releases](https://github.com/sigurdeye/QuickLog/releases) page.
2. Run the executable. It will appear in your system tray.

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
