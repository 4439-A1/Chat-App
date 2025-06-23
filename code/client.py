import socket
import threading
import tkinter as tk
import tkinter.simpledialog

# HOST = 'localhost'
HOST = '192.168.1.194'
PORT = 12345

# === Functions ===
def start_chat():
    global current_chat
    user = recipient_entry.get().strip()
    if not user:
        return
    if user not in chat_log:
        chat_log[user] = []
        add_to_sidebar(user)
    current_chat = user
    refresh_chat_display()
    recipient_entry.delete(0, tk.END)

def switch_chat(user):
    global current_chat
    current_chat = user
    refresh_chat_display()

def refresh_chat_display():
    if current_chat is None:
        return
    chat_display.config(state=tk.NORMAL)
    chat_display.delete(1.0, tk.END)
    for msg in chat_log.get(current_chat, []):
        chat_display.insert(tk.END, msg + "\n")
    chat_display.config(state=tk.DISABLED)


def append_system(msg):
    chat_display.config(state=tk.NORMAL)
    chat_display.insert(tk.END, f"{msg}\n")
    chat_display.config(state=tk.DISABLED)

def add_to_sidebar(user):
    btn = tk.Button(sidebar, text=user, command=lambda u=user: switch_chat(u))
    btn.pack(fill=tk.X)

def receive():
    global current_chat
    while True:
        try:
            msg = client.recv(1024).decode()
            print(f"Received raw: {msg}")
            if msg.startswith("[INFO]"):
                append_system(msg)
            elif msg.startswith("[") and "]" in msg:
                sender = msg[1:msg.index("]")]
                content = msg[msg.index("]") + 2:]

                if sender not in chat_log:
                    chat_log[sender] = []
                    add_to_sidebar(sender)

                chat_log[sender].append(f"{sender}: {content}")

                # Auto-select sender if no current chat is open
                if current_chat is None:
                    switch_chat(sender)
                elif sender == current_chat:
                    refresh_chat_display()
        except:
            append_system("❌ Lost connection to server.")
            break

def send():
    msg = msg_entry.get().strip()
    if not msg:
        return
    if current_chat is None:
        append_system("⚠️ Please select a recipient from the left.")
        return
    try:
        full_msg = f"{current_chat}|{msg}"
        client.send(full_msg.encode())
        chat_log[current_chat].append(f"You: {msg}")
        refresh_chat_display()
    except:
        append_system("❌ Message failed to send.")
    msg_entry.delete(0, tk.END)

# === GUI Initialization ===
root = tk.Tk()
root.withdraw()
username = tk.simpledialog.askstring("Username", "Enter your username:")
if not username:
    exit()
password = tk.simpledialog.askstring("Password", "Enter your password:", show="*")
if not password:
    exit()
root.deiconify()
root.title(f"Chat Client - {username}")

# === Socket Setup ===
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    client.connect((HOST, PORT))
    credentials = f"{username}|{password}"
    client.send(credentials.encode())  # send username to server
    response = client.recv(1024).decode().split("\n")[0]
    if response != "OK":
        print("❌ Login failed:", response)
        exit()
except Exception as e:
    print(f"❌ Could not connect: {e}")
    exit()

connected = True

chat_log = {}        # {username: [message strings]}
current_chat = None  # which username is currently selected

# === GUI Layout ===
# Left sidebar for selecting users
sidebar = tk.Frame(root, width=150, bg="#dddddd")
sidebar.pack(side=tk.LEFT, fill=tk.Y)

# -- Entry at top of sidebar to start chat manually --
recipient_frame = tk.Frame(sidebar, bg="#dddddd")
recipient_frame.pack(padx=5, pady=5, anchor="nw")

recipient_label = tk.Label(recipient_frame, text="To:", bg="#dddddd")
recipient_label.pack(side=tk.LEFT)

recipient_entry = tk.Entry(recipient_frame, width=12)
recipient_entry.pack(side=tk.LEFT, padx=(5, 0))

start_btn = tk.Button(recipient_frame, text="▶", command=start_chat, width=2)
start_btn.pack(side=tk.LEFT, padx=5)

# Right side for chat messages and input
chat_frame = tk.Frame(root)
chat_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

chat_display = tk.Text(chat_frame, state=tk.DISABLED)
chat_display.pack(fill=tk.BOTH, expand=True)

msg_entry = tk.Entry(chat_frame)
msg_entry.pack(fill=tk.X)

send_btn = tk.Button(chat_frame, text="Send")
send_btn.pack()

# === Setup and Start ===
send_btn.config(command=send)
threading.Thread(target=receive, daemon=True).start()
root.mainloop()
