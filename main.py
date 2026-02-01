import json
import os
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk
import pystray
from PIL import Image, ImageDraw
import keyboard

class TodoManager:
    def __init__(self):
        self.config_path = Path.home() / ".minimal_todo.json"
        data = self.load_data()
        self.todos = data.get("todos", [])
        self.notes = data.get("notes", [])
        self.marks = data.get("marks", [])

    def load_data(self):
        if self.config_path.exists():
            try:
                # If file exists but is empty, it might be mid-corruption
                if self.config_path.stat().st_size == 0:
                    return {"todos": [], "notes": [], "marks": []}

                with open(self.config_path, "r", encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Handle old format (direct list of todos)
                    if isinstance(data, list):
                        todos = data
                        notes = []
                        marks = []
                    elif isinstance(data, dict):
                        todos = data.get("todos", [])
                        notes = data.get("notes", [])
                        marks = data.get("marks", [])
                    else:
                        todos = []
                        notes = []
                        marks = []

                    # Migration: ensure every todo has a 'done' key
                    changed = False
                    for item in todos:
                        if isinstance(item, dict) and 'done' not in item:
                            item['done'] = False
                            changed = True
                    
                    if changed:
                        self.save_data_raw(todos, notes, marks)
                    
                    return {"todos": todos, "notes": notes, "marks": marks}
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
                return {"todos": [], "notes": [], "marks": []}
        return {"todos": [], "notes": [], "marks": []}

    def save_data_raw(self, todos, notes, marks):
        # Atomic write: Save to temp file then replace
        temp_path = self.config_path.with_suffix(".json.tmp")
        try:
            with open(temp_path, "w", encoding='utf-8') as f:
                json.dump({"todos": todos, "notes": notes, "marks": marks}, f, ensure_ascii=False)
            
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
        self.save_data_raw(self.todos, self.notes, self.marks)

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
    def __init__(self, parent, callback, on_close=None, title="New Item", prompt="...", is_password=False):
        super().__init__(parent)
        self.callback = callback
        self.on_close = on_close
        self.prompt = prompt
        self.is_password = is_password
        
        # Remove window decorations (title bar, borders)
        self.overrideredirect(True)
        
        # Modern Dark "Glass" Styling
        bg_color = "#1e1e1e"
        self.configure(bg=bg_color)
        self.attributes("-alpha", 0.95)  # Semi-transparent
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

        # The Entry Field (No border, minimalist)
        self.entry = tk.Entry(self, font=("Segoe UI Variable Display", 14), 
                              bg=bg_color, fg="white", 
                              insertbackground="white", 
                              bd=0, highlightthickness=0,
                              show="*" if is_password else "",
                              justify="center")
        self.entry.pack(expand=True, fill="both", padx=20)
        
        # Placeholder/Prompt logic (Improved to avoid flicker)
        # We don't insert it immediately because we expect to gain focus.
        # If focus fails or is lost, we'll add it then.
        self.entry.bind("<FocusIn>", self._clear_placeholder)
        self.after(200, self._add_placeholder)

        # Bindings
        self.bind("<Return>", lambda e: self.submit())
        self.bind("<Escape>", lambda e: self.destroy())
        
        # Debounced closure to prevent accidental closure on creation
        self.ready_to_close = False
        self.after(500, self._set_ready_and_start_monitor)
        self.bind("<FocusOut>", self._on_focus_out)
        
        # Initial focus and grab
        self.after(10, self._force_focus)

    def _set_ready_and_start_monitor(self):
        self.ready_to_close = True
        self._poll_focus()

    def _on_focus_out(self, event):
        # We still use the event as a trigger, but with a "smart" check
        if self.ready_to_close:
            self.after(100, self._check_focus_and_close)

    def _poll_focus(self):
        """Smart polling monitor for focus loss."""
        if self.winfo_exists() and self.ready_to_close:
            self._check_focus_and_close()
            self.after(500, self._poll_focus)

    def _check_focus_and_close(self):
        """The 'smart' check: verifies if focus is truly outside our process."""
        if not self.winfo_exists():
            return
            
        try:
            import ctypes
            import os
            # Get the HWND of the window that currently has focus
            foreground_hwnd = ctypes.windll.user32.GetForegroundWindow()
            
            # If no window has focus, or it's us, we stay open
            if foreground_hwnd == 0:
                return
                
            # Get our own HWND
            my_hwnd = self.winfo_id()
            if foreground_hwnd == my_hwnd:
                return
                
            # If it's not us, check if it's one of our own process's windows
            # (e.g. if we had multiple dialogs or a root window visible)
            lp_pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(foreground_hwnd, ctypes.byref(lp_pid))
            
            if lp_pid.value != os.getpid():
                self.destroy()
        except Exception:
            # Fallback for unexpected errors
            if self.focus_get() is None:
                self.destroy()

    def _force_focus(self):
        self.attributes("-topmost", True)
        self.focus_force()
        self.lift()
        self.entry.focus_set()
        
        # Direct Windows API call to steal foreground focus
        try:
            import ctypes
            # Get the window handle (HWND)
            hwnd = self.winfo_id()
            
            # SWP_NOSIZE (1) | SWP_NOMOVE (2) | SWP_SHOWWINDOW (64) = 67
            # HWND_TOPMOST = -1
            ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 67)
            
            # Try to bring to front using multiple methods
            ctypes.windll.user32.ShowWindow(hwnd, 5) # SW_SHOW
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            ctypes.windll.user32.SetActiveWindow(hwnd)
            
            # Additional trick: attach to the foreground window thread
            # to gain permission to SetForegroundWindow
            curr_thread = ctypes.windll.kernel32.GetCurrentThreadId()
            fore_window = ctypes.windll.user32.GetForegroundWindow()
            if fore_window != 0:
                fore_thread = ctypes.windll.user32.GetWindowThreadProcessId(fore_window, None)
                if curr_thread != fore_thread:
                    ctypes.windll.user32.AttachThreadInput(fore_thread, curr_thread, True)
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                    ctypes.windll.user32.AttachThreadInput(fore_thread, curr_thread, False)
            
            # Final attempt to ensure focus lands on the Entry specifically
            self.entry.focus_set()
        except Exception as e:
            print(f"Focus error: {e}")

        # Repeated focus attempts for stubborn windows
        self.after(50, lambda: self.focus_force())
        self.after(50, lambda: self.entry.focus_set())
        self.after(150, lambda: self.entry.focus_set())

    def _clear_placeholder(self, event=None):
        if self.entry.get() == self.prompt:
            self.entry.delete(0, tk.END)
            self.entry.config(fg="white")
            if self.is_password:
                self.entry.config(show="*")

    def _add_placeholder(self, event=None):
        if self.winfo_exists() and not self.entry.get() and self.focus_get() != self.entry:
            self.entry.config(fg="#888888")
            if self.is_password:
                self.entry.config(show="") # Show prompt text unmasked
            self.entry.insert(0, self.prompt)

    def destroy(self):
        if self.on_close:
            self.on_close()
        super().destroy()

    def submit(self):
        text = self.entry.get()
        # Don't submit if it's just the placeholder
        if text.strip() and text not in ["What needs to be done?", "Enter your note:", "Enter text:"]:
            self.callback(text)
        self.destroy()

class TrayApp:
    def __init__(self):
        self.manager = TodoManager()
        self.icon = None
        self.mode = "todo"  # "todo", "note", or "mark"
        self.current_dialog = None
        
        # Create a hidden root window to handle the main event loop
        self.root = tk.Tk()
        self.root.withdraw()
        
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
        if self.mode == "todo":
            self.mode = "note"
        elif self.mode == "note":
            self.mode = "mark"
        else:
            self.mode = "todo"
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

        if self.mode == "todo":
            title, prompt, is_pw = "New Task", "What needs to be done?", False
        elif self.mode == "note":
            title, prompt, is_pw = "New Note", "Enter your note:", False
        else: # mark mode
            title, prompt, is_pw = "Add", "Enter text:", True
            
        def clear_current_dialog():
            self.current_dialog = None

        self.current_dialog = TaskDialog(self.root, self.on_item_added, on_close=clear_current_dialog, title=title, prompt=prompt, is_password=is_pw)
        self.current_dialog.focus_force()  # Initial attempt to grab focus immediately

    def on_item_added(self, text):
        if self.mode == "todo":
            self.manager.add_todo(text)
        elif self.mode == "note":
            self.manager.add_note(text)
        else:
            self.manager.add_mark(text)
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

        # Determine icon status for todo mode
        all_completed = True
        if self.manager.todos:
            all_completed = all(t['done'] for t in self.manager.todos)
        
        # Update icon image
        if self.icon:
            self.icon.icon = self.create_image(all_completed)

        menu_items = []
        
        # Left-click default action: Toggle Mode (Invisible)
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
            # In mark mode, the entries are hidden in a submenu called "Logs" or similar
            marks_items = []
            if not self.manager.marks:
                marks_items.append(pystray.MenuItem("Empty", lambda: None, enabled=False))
            else:
                for i, mark in enumerate(self.manager.marks):
                    # Clicking a mark deletes it (as requested)
                    marks_items.append(pystray.MenuItem(mark, (lambda idx=i: lambda: self.on_delete_mark(idx))()))
                
                marks_items.append(pystray.Menu.SEPARATOR)
                marks_items.append(pystray.MenuItem("CLEAR ALL", self.on_clear_marks))
            
            # The main menu for Mark Mode is very sparse
            menu_items.append(pystray.MenuItem("Logs", pystray.Menu(*marks_items)))
            menu_items.append(pystray.Menu.SEPARATOR)
            menu_items.append(pystray.MenuItem("Add", self.add_item_ui))

        menu_items.append(pystray.Menu.SEPARATOR)
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
        try:
            # We use suppress=True to prevent the character from being typed into other apps
            # and to stop it from interfering with our new window's focus
            keyboard.add_hotkey('|', lambda: self.root.after(0, self.add_item_ui), suppress=True)
            keyboard.add_hotkey('alt+|', lambda: self.root.after(0, self.toggle_mode), suppress=True)
        except Exception as e:
            print(f"Error registering hotkeys: {e}")

        self.icon = pystray.Icon("quick_log", self.create_image(all_completed), "Quick Log")
        self.update_menu()
        self.icon.run()

    def run(self):
        # Start pystray in a separate thread
        tray_thread = threading.Thread(target=self.run_tray, daemon=True)
        tray_thread.start()
        
        # Run Tkinter main loop in the main thread
        self.root.mainloop()

if __name__ == "__main__":
    app = TrayApp()
    app.run()
