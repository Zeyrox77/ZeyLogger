<<<<<<< HEAD
# 🔑 KeyLogger — Educational Keystroke & Clipboard Monitor

> ⚠️ **This project is for educational purposes only.**
> It was created to demonstrate how network sockets, threading, and system-level monitoring work in Python. Do **not** use this software on systems you do not own or without explicit permission from the system owner. Unauthorized use may be illegal.

---

## 📖 Overview

This project consists of two Python scripts that together form a client-server keystroke and clipboard monitoring system. It is intended purely as a learning resource for understanding:

- TCP socket programming in Python
- Multi-threaded application design
- Global keyboard event listening via `pynput`
- System resource monitoring with `psutil`
- Building GUI applications with `tkinter`
- Windows Registry manipulation for startup entries

---

## 📁 Project Structure

```
KeyLogger/
├── client.py          # Runs on the monitored machine — captures keystrokes & clipboard
├── server.py          # Runs on the receiving machine — displays incoming data in a GUI
└── requirements.txt   # Python dependencies
```

---

## ⚙️ How It Works

### `client.py` — The Agent

Runs on the machine to be monitored. It performs three tasks simultaneously:

1. **Keystroke Capture** — Uses `pynput` to listen globally for every key press and queues it for transmission.
2. **Clipboard Monitoring** — Polls the system clipboard every second using `pyperclip` and detects changes.
3. **Network Transmission** — Opens a persistent TCP socket to the server and forwards captured data using a 4-byte length-prefixed protocol.

It also launches a small `tkinter` GUI showing live CPU, RAM, and Disk usage as a decoy window. Closing the window does **not** stop the background monitoring process.

On Windows, it can optionally register itself in the `HKCU\...\Run` registry key to persist across reboots.

### `server.py` — The Receiver

Runs on the attacker's / researcher's machine. It:

1. Listens for incoming TCP connections on a configurable host and port.
2. Spawns a dedicated thread per connected client.
3. Displays each client in its own tab in a `ttk.Notebook` GUI.
4. Separates keystrokes and clipboard events into two labeled panels with color-coded timestamps.

Multiple clients can connect simultaneously.

---

## 🚀 Setup & Usage

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**`requirements.txt`:**
```
pynput
pyperclip
psutil
```

> Standard library modules used (`tkinter`, `socket`, `threading`, `struct`, `queue`, etc.) require no installation.

### 2. Configure the Client

Open `client.py` and set the server's IP address:

```python
SERVER_HOST = '127.0.0.1'  # <-- Change to your server's IP
SERVER_PORT = 9998
```

### 3. Start the Server

Run on the receiving machine:

```bash
python server.py
```

The GUI will launch and begin listening on `0.0.0.0:9998`.

### 4. Start the Client

Run on the monitored machine:

```bash
python client.py
```

The client will connect to the server and begin transmitting events.

---

## 🧠 Key Technical Concepts

| Concept | Where it appears |
|---|---|
| Length-prefixed TCP framing | `send_message()` / `receive_full_message()` |
| Thread-safe UI updates via queue | `data_queue` + `process_queue()` in server |
| Global keyboard hook | `pynput.keyboard.Listener` in client |
| Daemon vs. non-daemon processes | `multiprocessing.Process(daemon=False)` |
| Windows Registry autostart | `winreg` in `add_to_autostart()` |
| Multi-client tabbed GUI | `ttk.Notebook` with dynamic tab creation |

---

## ⚠️ Legal & Ethical Disclaimer

This software is provided **strictly for educational and research purposes**. The authors do not condone or support any use of this code for unauthorized surveillance, privacy violations, or any other illegal activities.

**Before running this software:**
- Ensure you have explicit, written consent from the owner of any machine you run the client on.
- Be aware that keyloggers may be illegal in your jurisdiction without consent.
- Never deploy this on public or shared networks.

**The authors assume no liability for misuse of this code.**

---

## 📚 Learning Resources

If this project sparked your interest, here are some topics to explore further:

- [Python `socket` documentation](https://docs.python.org/3/library/socket.html)
- [pynput documentation](https://pynput.readthedocs.io/)
- [Python Threading](https://docs.python.org/3/library/threading.html)
- [Tkinter GUI Guide](https://docs.python.org/3/library/tkinter.html)

---

## 📄 License

This project is released for educational use only. No warranty is provided. Use responsibly.
=======
# ZeyLogger
Educational keylogger &amp; clipboard monitor with a multi-client server GUI — for learning purposes only.
>>>>>>> 96aec75b1263d8c16e215b0a001eba5307294b88
