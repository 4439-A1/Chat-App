import socket
import threading
import tkinter as tk
import tkinter.simpledialog
import os
import json
import re

# HOST = 'localhost'
HOST = '192.168.1.194'
PORT = 12345

CONFIG_PATH = os.path.expanduser("~/.chatclient_config.json")

def load_credentials():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return None

def save_credentials(username, password):
    with open(CONFIG_PATH, "w") as f:
        json.dump({"username": username, "password": password}, f)

def clear_credentials():
    if os.path.exists(CONFIG_PATH):
        os.remove(CONFIG_PATH)

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
    status_label.config(state=tk.NORMAL)
    status_label.insert(tk.END, f"{msg}\n")
    status_label.config(state=tk.DISABLED)

def add_to_sidebar(user):
    btn = tk.Button(sidebar, text=user, command=lambda u=user: switch_chat(u))
    btn.pack(fill=tk.X)

def receive():
    print("received")
    global current_chat
    buffer = ""
    while True:
        try:
            buffer += client.recv(1024).decode()
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if line.strip():
                    print(f"Received: {line}")
                    process_message(line.strip())
        except:
            append_system("❌ Lost connection to server.")
            break

def process_message(msg):
    global current_chat
    if msg.startswith("[INFO]"):
        append_system(msg)
    elif msg.startswith("["):
        match = re.match(r"\[(.*?)\]\[(.*?)\] (.*)", msg)
        other_user = match.group(1)
        sender = match.group(2)
        content = match.group(3)
        
        partner = other_user
        
        if sender == username:
            display_msg = f"You: {content}"  # remove "username: " prefix
        else:
            display_msg = f"{sender}: {content}"

        if partner not in chat_log:
            chat_log[partner] = []
            add_to_sidebar(partner)

        chat_log[partner].append(display_msg)

        if current_chat is None:
            switch_chat(partner)
        elif current_chat == partner:
            refresh_chat_display()

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
        msg_entry.delete(0, tk.END)
        chat_log[current_chat].append(f"You: {msg}")
        refresh_chat_display()
    except:
        append_system("❌ Message failed to send.")
        msg_entry.delete(0, tk.END)
    # msg_entry.delete(0, tk.END)

def logout():
    clear_credentials()
    append_system("🔁 Logged out. Please restart the app.")
    client.close()
    root.quit()

# === GUI Initialization ===
root = tk.Tk()
root.withdraw()

creds = load_credentials()
if creds:
    username = creds["username"]
    password = creds["password"]
else:
    username = tk.simpledialog.askstring("Username", "Enter your username:")
    if not username:
        exit()
    password = tk.simpledialog.askstring("Password", "Enter your password:", show = "*")
    if not password:
        exit()
    save_credentials(username, password)

# === GUI Setup ===
root.deiconify()
root.title(f"Chat Client - {username}")

# === Socket Setup ===
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    client.connect((HOST, PORT))
    credentials = f"{username}|{password}"
    client.send(credentials.encode()) # send username to server
    response = client.recv(1024).decode().split("\n")[0]
    if response != "OK":
        print("❌ Login failed:", response)
        clear_credentials()
        exit()
except Exception as e:
    print(f"❌ Could not connect: {e}")
    exit()

connected = True

chat_log = {}        # {username: [message strings]}
current_chat = None  # which username is currently selected

# === GUI Layout ===
# Left sidebar for selecting users
sidebar = tk.Frame(root, width=200)
sidebar.pack(side=tk.LEFT, fill=tk.Y)
sidebar.pack_propagate(False)

# -- Entry at top of sidebar to start chat manually --
recipient_frame = tk.Frame(sidebar)
recipient_frame.pack(padx=5, pady=5, anchor="nw")

# Recipient entry and button
recipient_label = tk.Label(recipient_frame, text="To:")
recipient_label.pack(side=tk.LEFT)

recipient_entry = tk.Entry(recipient_frame, width=9)
recipient_entry.pack(side=tk.LEFT, padx=(5, 0))
recipient_entry.bind("<Return>", lambda event: start_chat())

start_btn = tk.Button(recipient_frame, text="▶", command=start_chat, width=2)
start_btn.pack(side=tk.LEFT, padx=5)

# Status box
status_frame = tk.Frame(sidebar, height=50)
status_frame.pack(side=tk.BOTTOM, fill=tk.X)

status_label = tk.Text(status_frame, height=5, state=tk.DISABLED, bg="#4a4a4a", fg="white")
status_label.pack(fill=tk.X, padx=5, pady=5)

# Right side for chat messages and input
chat_frame = tk.Frame(root)
chat_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

chat_display = tk.Text(chat_frame, state=tk.DISABLED)
chat_display.pack(fill=tk.BOTH, expand=True)

msg_entry_frame = tk.Frame(chat_frame)
msg_entry_frame.pack(fill=tk.X)

msg_entry = tk.Entry(msg_entry_frame)
msg_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
msg_entry.bind("<Return>", lambda event: send()) # Press enter to send

send_btn = tk.Button(msg_entry_frame, text="Send")
send_btn.pack(side=tk.RIGHT)

menu_bar = tk.Menu(root)
account_menu = tk.Menu(menu_bar, tearoff=0)
account_menu.add_command(label="Logout", command=logout)
menu_bar.add_cascade(label="Account", menu=account_menu)
root.config(menu=menu_bar)

# === Setup and Start ===
send_btn.config(command=send)
threading.Thread(target=receive, daemon=True).start()
root.mainloop()
