import json
import os
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk
import pystray
from PIL import Image, ImageDraw
import time
import win32api
import win32gui
import win32con
from pynput import keyboard

class TodoManager:
    def __init__(self):
        self.config_path = Path.home() / ".quicklog.json"
        
        # Migration: check for old config file
        old_config = Path.home() / ".minimal_todo.json"
        if old_config.exists() and not self.config_path.exists():
            try:
                import shutil
                shutil.copy2(old_config, self.config_path)
            except:
                pass

        data = self.load_data()
        self.todos = data.get("todos", [])
        self.notes = data.get("notes", [])
        self.marks = data.get("marks", [])
        self.settings = data.get("settings", self.get_default_settings())

    def get_default_settings(self):
        return {
            "modes": {
                "todo": {"enabled": True, "password": False},
                "note": {"enabled": True, "password": False},
                "mark": {"enabled": True, "password": True}
            },
            "shortcuts": {
                "open_bar": "<alt>+q",
                "cycle_mode": "<ctrl>+q"
            }
        }

    def load_data(self):
        if self.config_path.exists():
            try:
                # If file exists but is empty, it might be mid-corruption
                if self.config_path.stat().st_size == 0:
                    return {"todos": [], "notes": [], "marks": [], "settings": self.get_default_settings()}

                with open(self.config_path, "r", encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Handle old format (direct list of todos)
                    if isinstance(data, list):
                        todos = data
                        notes = []
                        marks = []
                        settings = self.get_default_settings()
                    elif isinstance(data, dict):
                        todos = data.get("todos", [])
                        notes = data.get("notes", [])
                        marks = data.get("marks", [])
                        settings = data.get("settings", self.get_default_settings())
                    else:
                        todos = []
                        notes = []
                        marks = []
                        settings = self.get_default_settings()

                    # Migration: ensure every todo has a 'done' key
                    changed = False
                    for item in todos:
                        if isinstance(item, dict) and 'done' not in item:
                            item['done'] = False
                            changed = True
                    
                    if changed:
                        self.save_data_raw(todos, notes, marks, settings)
                    
                    return {"todos": todos, "notes": notes, "marks": marks, "settings": settings}
            except (json.JSONDecodeError, Exception) as e:
                # If corruption is detected, we don't overwrite immediately
                # We could log this or create a backup of the corrupted file
                print(f"Error loading data: {e}")
                backup_path = self.config_path.with_suffix(".json.bak")
                try:
                    import shutil
                    if self.config_path.exists():
                        shutil.copy2(self.config_path, backup_path)
                except:
                    pass
                return {"todos": [], "notes": [], "marks": [], "settings": self.get_default_settings()}
        return {"todos": [], "notes": [], "marks": [], "settings": self.get_default_settings()}

    def save_data_raw(self, todos, notes, marks, settings):
        # Atomic write: Save to temp file then replace
        temp_path = self.config_path.with_suffix(".json.tmp")
        try:
            with open(temp_path, "w", encoding='utf-8') as f:
                json.dump({
                    "todos": todos, 
                    "notes": notes, 
                    "marks": marks,
                    "settings": settings
                }, f, ensure_ascii=False)
            
            # os.replace is atomic on both Windows and POSIX
            os.replace(temp_path, self.config_path)
        except Exception as e:
            print(f"Error saving data: {e}")
            if temp_path.exists():
                try:
                    os.remove(temp_path)
                except:
                    pass

    def save_data(self):
        self.save_data_raw(self.todos, self.notes, self.marks, self.settings)

    def add_todo(self, text):
        if text and text.strip():
            self.todos.append({"text": text.strip(), "done": False})
            self.save_data()
            return True
        return False

    def toggle_todo(self, index):
        if 0 <= index < len(self.todos):
            self.todos[index]["done"] = not self.todos[index]["done"]
            self.save_data()

    def delete_todo(self, index):
        if 0 <= index < len(self.todos):
            self.todos.pop(index)
            self.save_data()

    def clear_completed(self):
        self.todos = [t for t in self.todos if not t['done']]
        self.save_data()

    def add_note(self, text):
        if text and text.strip():
            self.notes.append(text.strip())
            self.save_data()
            return True
        return False

    def delete_note(self, index):
        if 0 <= index < len(self.notes):
            self.notes.pop(index)
            self.save_data()

    def add_mark(self, text):
        if text and text.strip():
            timestamp = datetime.now().strftime("[%H:%M]")
            self.marks.append(f"{timestamp} {text.strip()}")
            self.save_data()
            return True
        return False

    def delete_mark(self, index):
        if 0 <= index < len(self.marks):
            self.marks.pop(index)
            self.save_data()

    def clear_all_marks(self):
        self.marks = []
        self.save_data()

class TaskDialog(tk.Toplevel):
    """A frameless, minimalist floating input dialog."""
    def __init__(self, parent_app, callback, on_close=None, title="New Item", prompt="...", is_password=False):
        super().__init__(parent_app.root)
        self.parent = parent_app
        self.callback = callback
        self.on_close = on_close
        self.prompt = prompt
        self.is_password = is_password
        
        # Remove window decorations (title bar, borders)
        self.overrideredirect(True)
        
        # Modern Dark "Glass" Styling
        bg_color = "#121212"
        self.configure(bg=bg_color)
        self.attributes("-alpha", 0.98)
        self.attributes("-topmost", True)
        
        # Dimensions
        width, height = 400, 60
        self.geometry(f"{width}x{height}")
        
        # Center on screen
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")

        # The Entry Field
        self.entry = tk.Entry(self, font=("Segoe UI Variable Display", 14), 
                              bg=bg_color, fg="white", 
                              insertbackground="white", 
                              bd=0, highlightthickness=0,
                              show="*" if is_password else "",
                              justify="center")
        self.entry.pack(expand=True, fill="both", padx=20)
        
        self.entry.bind("<FocusIn>", self._handle_focus_in)
        self.after(200, self._add_placeholder)

        # Focus state tracking
        self.has_had_focus = False
        self.launch_time = time.time()

        # Bindings
        self.bind("<Return>", lambda e: self.submit())
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Button-3>", self._show_context_menu) # Right click
        
        # Debounced closure
        self.ready_to_close = False
        self.after(1500, self._set_ready_and_start_monitor)
        self.bind("<FocusOut>", self._on_focus_out)
        self.after(10, self._force_focus)
        self.after(500, self._force_focus) # Retry focus once more

    def _show_context_menu(self, event):
        # Create a standard old-school gray menu
        menu = tk.Menu(self, tearoff=0, bg="#f0f0f0", fg="black")
        
        def toggle(m, s):
            self.parent.manager.settings["modes"][m][s] = not self.parent.manager.settings["modes"][m][s]
            # Ensure at least one enabled
            if s == "enabled" and not any(self.parent.manager.settings["modes"][mi]["enabled"] for mi in ["todo", "note", "mark"]):
                self.parent.manager.settings["modes"][m]["enabled"] = True
            self.parent.manager.save_data()
            self.parent.on_settings_saved()

        for mode in ["todo", "note", "mark"]:
            mode_menu = tk.Menu(menu, tearoff=0)
            is_enabled = self.parent.manager.settings["modes"][mode]["enabled"]
            is_masked = self.parent.manager.settings["modes"][mode]["password"]
            
            mode_menu.add_checkbutton(label="Enable", 
                                      command=lambda m=mode: toggle(m, "enabled"),
                                      variable=tk.BooleanVar(value=is_enabled))
            mode_menu.add_checkbutton(label="Mask Input", 
                                      command=lambda m=mode: toggle(m, "password"),
                                      variable=tk.BooleanVar(value=is_masked))
            menu.add_cascade(label=f"{mode.capitalize()} Mode", menu=mode_menu)

        menu.add_separator()
        startup_text = "Remove from Startup" if self.parent.is_startup_enabled() else "Run at Startup"
        menu.add_command(label=startup_text, 
                         command=lambda: self.parent.set_startup(not self.parent.is_startup_enabled()))
        
        menu.post(event.x_root, event.y_root)

    def _set_ready_and_start_monitor(self):
        self.ready_to_close = True
        self._poll_focus()

    def _on_focus_out(self, event):
        if self.ready_to_close:
            self.after(100, self._check_focus_and_close)

    def _poll_focus(self):
        if self.winfo_exists() and self.ready_to_close:
            self._check_focus_and_close()
            self.after(500, self._poll_focus)

    def _check_focus_and_close(self):
        if not self.winfo_exists(): return
        
        # Don't auto-close for the first 5 seconds unless we've actually HAD focus at some point
        # This prevents the window from closing immediately if focus-stealing is slow.
        if not self.has_had_focus and (time.time() - self.launch_time < 5.0):
            return

        try:
            import ctypes
            import os
            foreground_hwnd = ctypes.windll.user32.GetForegroundWindow()
            if foreground_hwnd == 0: return
            my_hwnd = self.winfo_id()
            if foreground_hwnd == my_hwnd: return
            
            # Use Tcl's focus check as well
            if self.focus_get() is not None: return

            lp_pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(foreground_hwnd, ctypes.byref(lp_pid))
            if lp_pid.value != os.getpid():
                self.destroy()
        except:
            if self.focus_get() is None: self.destroy()

    def _handle_focus_in(self, event=None):
        self.has_had_focus = True
        self._clear_placeholder(event)

    def _force_focus(self):
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.focus_force()
        self.entry.focus_set()
        
        try:
            import ctypes
            hwnd = self.winfo_id()
            
            # The "Alt" trick to bypass SetForegroundWindow restrictions
            # Simulate an Alt key press (0x12)
            ctypes.windll.user32.keybd_event(0x12, 0, 0, 0) # Alt Down
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            ctypes.windll.user32.keybd_event(0x12, 0, 2, 0) # Alt Up
            
            # Ensure window is shown and positioned top-most
            ctypes.windll.user32.ShowWindow(hwnd, 5) # SW_SHOW
            ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0040 | 0x0001 | 0x0002) # HWND_TOPMOST, NOSIZE, NOMOVE
        except: pass
        
        # Final focused sets
        self.after(50, lambda: self.entry.focus_set())
        self.after(150, lambda: self.entry.focus_set())

    def _clear_placeholder(self, event=None):
        if self.entry.get() == self.prompt:
            self.entry.delete(0, tk.END)
            self.entry.config(fg="white")
            if self.is_password: self.entry.config(show="*")

    def _add_placeholder(self, event=None):
        if self.winfo_exists() and not self.entry.get() and self.focus_get() != self.entry:
            self.entry.config(fg="#666666")
            if self.is_password: self.entry.config(show="")
            self.entry.insert(0, self.prompt)

    def destroy(self):
        if self.on_close: self.on_close()
        super().destroy()

    def submit(self):
        text = self.entry.get()
        if text.strip() and text not in [self.prompt]:
            self.callback(text)
        self.destroy()

# SettingsDialog removed.

class TrayApp:
    def __init__(self):
        self.manager = TodoManager()
        self.icon = None
        self.mode = "todo"  # "todo", "note", or "mark"
        self.current_dialog = None
        self.hotkey_listener = None
        self.last_wake_check = time.time()
        
        # Create a hidden root window to handle the main event loop
        self.root = tk.Tk()
        self.root.withdraw()

        if not (Path.home() / ".quicklog.json").exists() and not (Path.home() / ".minimal_todo.json").exists():
            # First launch: add instructional todos
            self.manager.add_todo("Press alt+Q to add a note")
            self.manager.add_todo("Press ctrl+Q to switch mode")
            self.manager.save_data()
        
    def create_image(self, all_completed=False):
        image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        dc = ImageDraw.Draw(image)
        
        # Consistent background
        if self.mode == "todo":
            bg_color = (45, 45, 45, 255)
        elif self.mode == "note":
            bg_color = (234, 179, 8, 255) # Yellow
        else: # mark mode
            bg_color = (239, 68, 68, 255) # Red
            
        dc.rounded_rectangle([8, 8, 56, 56], radius=12, fill=bg_color)
        
        if self.mode == "todo":
            # Yellow if tasks pending, Green if all completed
            color = '#22c55e' if all_completed else '#eab308'
            dc.line((20, 32, 30, 42), fill=color, width=5)
            dc.line((30, 42, 48, 24), fill=color, width=5)
        elif self.mode == "note":
            # Draw a simple white note icon
            dc.rectangle([20, 20, 44, 44], outline="white", width=3)
            dc.line((25, 28, 39, 28), fill="white", width=2)
            dc.line((25, 36, 39, 36), fill="white", width=2)
        else: # mark mode
            # Subtle generic icon (a small center dot)
            dc.ellipse([28, 28, 36, 36], fill="white")
            
        return image

    def toggle_mode(self):
        modes = ["todo", "note", "mark"]
        current_idx = modes.index(self.mode)
        
        # Try to find the next enabled mode
        for i in range(1, 4):
            next_mode = modes[(current_idx + i) % 3]
            if self.manager.settings["modes"][next_mode]["enabled"]:
                self.mode = next_mode
                break
        
        self.update_menu()

    def add_item_ui(self):
        # If a dialog already exists, just focus it and return
        if self.current_dialog is not None:
            try:
                if self.current_dialog.winfo_exists():
                    self.current_dialog.after(0, self.current_dialog._force_focus)
                    return
            except tk.TclError:
                self.current_dialog = None

        mode_settings = self.manager.settings["modes"].get(self.mode, {"enabled": True, "password": False})
        is_pw = mode_settings.get("password", False)

        if self.mode == "todo":
            title, prompt = "New Task", "..."
        elif self.mode == "note":
            title, prompt = "New Note", "..."
        else: # mark mode
            title, prompt = "Add", "..."
            
        def clear_current_dialog():
            self.current_dialog = None

        self.current_dialog = TaskDialog(self, self.on_item_added, on_close=clear_current_dialog, title=title, prompt=prompt, is_password=is_pw)
        self.current_dialog.focus_force()

    def on_item_added(self, text):
        if self.mode == "todo":
            self.manager.add_todo(text)
        elif self.mode == "note":
            self.manager.add_note(text)
        else:
            self.manager.add_mark(text)
        self.update_menu()

    def on_settings_saved(self):
        # Ensure current mode is still enabled
        if not self.manager.settings["modes"][self.mode]["enabled"]:
            self.toggle_mode()
        self.register_hotkeys() # Apply new hotkeys immediately
        self.update_menu()

    def on_clear_completed(self):
        self.manager.clear_completed()
        self.update_menu()

    def on_copy_note(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()

    def on_delete_note(self, index):
        self.manager.delete_note(index)
        self.update_menu()

    def on_delete_mark(self, index):
        self.manager.delete_mark(index)
        self.update_menu()

    def on_clear_marks(self):
        self.manager.clear_all_marks()
        self.update_menu()

    def update_menu(self):
        def on_toggle_todo(index):
            self.manager.toggle_todo(index)
            self.update_menu()

        def toggle_setting(mode, setting):
            self.manager.settings["modes"][mode][setting] = not self.manager.settings["modes"][mode][setting]
            # If disabling a mode, ensure at least one is enabled
            if setting == "enabled" and not any(self.manager.settings["modes"][m]["enabled"] for m in ["todo", "note", "mark"]):
                self.manager.settings["modes"][mode]["enabled"] = True
            
            self.manager.save_data()
            self.on_settings_saved()

        all_completed = True
        if self.manager.todos:
            all_completed = all(t['done'] for t in self.manager.todos)
        
        if self.icon:
            self.icon.icon = self.create_image(all_completed)

        menu_items = []
        menu_items.append(pystray.MenuItem("Toggle Mode", self.toggle_mode, default=True, visible=False))

        if self.mode == "todo":
            if not self.manager.todos:
                menu_items.append(pystray.MenuItem("No tasks yet", lambda: None, enabled=False))
            else:
                for i, todo in enumerate(self.manager.todos):
                    status = "✅" if todo['done'] else "⬜"
                    text = f"{status} {todo['text']}"
                    menu_items.append(pystray.MenuItem(text, (lambda idx=i: lambda: on_toggle_todo(idx))()))
            menu_items.append(pystray.Menu.SEPARATOR)
            menu_items.append(pystray.MenuItem("➕ Add Task...", self.add_item_ui))
            has_completed = any(t['done'] for t in self.manager.todos)
            if has_completed:
                menu_items.append(pystray.MenuItem("🧹 Clear completed tasks", self.on_clear_completed))
        
        elif self.mode == "note":
            if not self.manager.notes:
                menu_items.append(pystray.MenuItem("No notes yet", lambda: None, enabled=False))
            else:
                for i, note in enumerate(self.manager.notes):
                    note_menu = pystray.Menu(
                        pystray.MenuItem("📋 Copy", (lambda t=note: lambda: self.on_copy_note(t))()),
                        pystray.MenuItem("🗑️ Delete", (lambda idx=i: lambda: self.on_delete_note(idx))())
                    )
                    menu_items.append(pystray.MenuItem(note, note_menu))
            menu_items.append(pystray.Menu.SEPARATOR)
            menu_items.append(pystray.MenuItem("➕ Add Note...", self.add_item_ui))
        
        else: # mark mode
            marks_items = []
            if not self.manager.marks:
                marks_items.append(pystray.MenuItem("Empty", lambda: None, enabled=False))
            else:
                for i, mark in enumerate(self.manager.marks):
                    marks_items.append(pystray.MenuItem(mark, (lambda idx=i: lambda: self.on_delete_mark(idx))()))
                marks_items.append(pystray.Menu.SEPARATOR)
                marks_items.append(pystray.MenuItem("CLEAR ALL", self.on_clear_marks))
            menu_items.append(pystray.MenuItem("Logs", pystray.Menu(*marks_items)))
            menu_items.append(pystray.Menu.SEPARATOR)
            menu_items.append(pystray.MenuItem("➕ Add", self.add_item_ui))

        menu_items.append(pystray.Menu.SEPARATOR)
        
        # --- Settings Submenu ---
        def make_mode_menu(m):
            return pystray.Menu(
                pystray.MenuItem("Enable", lambda item: toggle_setting(m, "enabled"), 
                                checked=lambda item: self.manager.settings["modes"][m]["enabled"]),
                pystray.MenuItem("Mask Input", lambda item: toggle_setting(m, "password"), 
                                checked=lambda item: self.manager.settings["modes"][m]["password"])
            )

        settings_menu = pystray.Menu(
            pystray.MenuItem(lambda item: "Remove from startup" if self.is_startup_enabled() else "Run at startup", 
                            lambda: self.set_startup(not self.is_startup_enabled())),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Todo Mode", make_mode_menu("todo")),
            pystray.MenuItem("Note Mode", make_mode_menu("note")),
            pystray.MenuItem("Log Mode", make_mode_menu("mark"))
        )
        
        menu_items.append(pystray.MenuItem("⚙️ Settings", settings_menu))
        menu_items.append(pystray.MenuItem("Exit", self.quit_app))
        
        if self.icon:
            self.icon.menu = pystray.Menu(*menu_items)

    def quit_app(self):
        self.icon.stop()
        self.root.after(0, self.root.destroy)

    def run_tray(self):
        # Initial check for completion status
        all_completed = True
        if self.manager.todos:
            all_completed = all(t['done'] for t in self.manager.todos)

        # Register global hotkeys
        self.register_hotkeys()

        self.icon = pystray.Icon("quick_log", self.create_image(all_completed), "Quick Log")
        self.update_menu()
        self.icon.run()

    def register_hotkeys(self):
        if self.hotkey_listener:
            try:
                self.hotkey_listener.stop()
            except:
                pass
        
        shortcuts = self.manager.settings.get("shortcuts", self.get_default_shortcuts())
        open_bar_hk = shortcuts.get("open_bar", "<alt>+q")
        cycle_mode_hk = shortcuts.get("cycle_mode", "<ctrl>+q")

        try:
            # pynput hotkeys
            self.hotkey_listener = keyboard.GlobalHotKeys({
                open_bar_hk: lambda: self.root.after(0, self.add_item_ui),
                cycle_mode_hk: lambda: self.root.after(0, self.toggle_mode)
            })
            self.hotkey_listener.start()
            print(f"Hotkeys registered: {open_bar_hk}, {cycle_mode_hk}")
        except Exception as e:
            print(f"Error registering hotkeys: {e}")

    def get_default_shortcuts(self):
        return {"open_bar": "<alt>+q", "cycle_mode": "<ctrl>+q"}

    def check_sleep_wake(self):
        """Watchdog to detect system sleep/wake by checking for time jumps."""
        current_time = time.time()
        # If more than 10 seconds have passed since the last check (and we poll every 5s),
        # it's likely the system was asleep.
        if current_time - self.last_wake_check > 10:
            print("System wake detected, re-registering hotkeys...")
            self.register_hotkeys()
        
        self.last_wake_check = current_time
        self.root.after(5000, self.check_sleep_wake)

    def is_startup_enabled(self):
        startup_folder = Path(os.getenv("APPDATA")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        return (startup_folder / "QuickLog.vbs").exists()

    def set_startup(self, enabled):
        import sys
        startup_folder = Path(os.getenv("APPDATA")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        vbs_path = startup_folder / "QuickLog.vbs"
        
        if enabled:
            try:
                exe_path = sys.executable
                # Get the absolute path to either the EXE or the main.py script
                if getattr(sys, 'frozen', False):
                    # Running as PyInstaller EXE
                    target = os.path.abspath(exe_path)
                    vbs_content = (
                        'Set WshShell = CreateObject("WScript.Shell")\n'
                        f'WshShell.Run """{target}""", 0, False\n'
                        'Set WshShell = Nothing'
                    )
                else:
                    # Running from source (using current venv pythonw)
                    pythonw = Path(sys.prefix) / "Scripts" / "pythonw.exe"
                    main_py = os.path.abspath(__file__)
                    vbs_content = (
                        'Set WshShell = CreateObject("WScript.Shell")\n'
                        f'WshShell.Run """{pythonw}"" ""{main_py}""", 0, False\n'
                        'Set WshShell = Nothing'
                    )
                
                with open(vbs_path, "w", encoding="utf-8") as f:
                    f.write(vbs_content)
            except Exception as e:
                print(f"Error enabling startup: {e}")
        else:
            if vbs_path.exists():
                try:
                    os.remove(vbs_path)
                except Exception as e:
                    print(f"Error disabling startup: {e}")
        
        self.root.after(0, self.update_menu)

    def run(self):
        # Start pystray in a separate thread
        tray_thread = threading.Thread(target=self.run_tray, daemon=True)
        tray_thread.start()
        
        # Start sleep/wake watchdog
        self.root.after(5000, self.check_sleep_wake)
        
        # Run Tkinter main loop in the main thread
        self.root.mainloop()

if __name__ == "__main__":
    app = TrayApp()
    app.run()
