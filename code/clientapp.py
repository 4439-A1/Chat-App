# clientapp.py
# A simple chat client application using sockets and Tkinter for GUI.

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as sympadding
import base64
import secrets

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
CHAT_HISTORY = os.path.expanduser("~/.chatclient_history.json")

def load_chat_history():
    if os.path.exists(CHAT_HISTORY):
        with open(CHAT_HISTORY, "r") as f:
            return json.load(f)
    return {}

def save_chat_history(chat_log):
    with open(CHAT_HISTORY, "w") as f:
        json.dump(chat_log, f)

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

# def receive():
#     print("received")
#     global current_chat
#     buffer = ""
#     while True:
#         try:
#             buffer += client.recv(8192).decode()
#             while "\n" in buffer:
#                 line, buffer = buffer.split("\n", 1)
#                 if line.strip():
#                     print(f"Received: {line}")
#                     if line.startswith("[PUBKEY]"):
#                         # Ignore or log [PUBKEY] messages if they are not expected
#                         append_system("Received public key data (handled during initialization).")
#                         continue
#                     process_message(line.strip())
#         except:
#             append_system("❌ Lost connection to server.")
#             break

def receive():
    print("received")
    global current_chat
    buffer = ""
    while True:
        try:
            data = client.recv(8192).decode()
            buffer += data
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if line:
                    print(f"Received: {line}")
                    if line.startswith("[PUBKEY]"):
                        append_system("Received public key data (handled during initialization).")
                        continue
                    if line.startswith("[PUBKEYRESP]"):
                        append_system("Received [PUBKEYRESP] in receive (handled by request_public_key).")
                        continue  # Let request_public_key handle this
                    process_message(line)
        except Exception as e:
            append_system(f"❌ Lost connection to server: {e}")
            break

def process_message(msg):
    global current_chat
    if msg.startswith("[INFO]"):
        append_system(msg)
        return

    match = re.match(r"\[(.*?)\]\[(.*?)\] (.*)", msg)
    if not match:
        append_system(f"⚠️ Could not parse message: {msg}")
        return

    other_user, sender, content = match.groups()
    partner = other_user

    # Attempt to decrypt if message looks encrypted
    decrypted_content = content
    try:
        parts = content.split("|")
        if len(parts) == 3:
            encrypted_key_b64, iv_b64, ciphertext_b64 = parts
            encrypted_key = base64.b64decode(encrypted_key_b64)
            iv = base64.b64decode(iv_b64)
            ciphertext = base64.b64decode(ciphertext_b64)

            # Decrypt AES key with our private key
            aes_key = private_key.decrypt(
                encrypted_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )

            # Decrypt the message using AES
            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
            decryptor = cipher.decryptor()
            padded_msg = decryptor.update(ciphertext) + decryptor.finalize()

            # Unpad the message
            unpadder = sympadding.PKCS7(128).unpadder()
            plaintext = unpadder.update(padded_msg) + unpadder.finalize()
            decrypted_content = plaintext.decode()
    except Exception as e:
        decrypted_content = "[🔒 Could not decrypt message]"

    # Display message
    if sender == username:
        display_msg = f"You: {decrypted_content}"
    else:
        display_msg = f"{sender}: {decrypted_content}"

    if partner not in chat_log:
        chat_log[partner] = []
        add_to_sidebar(partner)

    chat_log[partner].append(display_msg)
    save_chat_history(chat_log)

    if current_chat is None:
        switch_chat(partner)
    elif current_chat == partner:
        refresh_chat_display()

def request_public_key(user):
    try:
        client.send(f"[GETKEY]{user}".encode())
        buffer = ""
        while True:
            data = client.recv(4096).decode()
            buffer += data
            # Check for complete [PUBKEYRESP] message (ends with -----END PUBLIC KEY-----\n)
            if "[PUBKEYRESP]" in buffer and "-----END PUBLIC KEY-----\n" in buffer:
                start_idx = buffer.index("[PUBKEYRESP]") + len("[PUBKEYRESP]")
                end_idx = buffer.index("-----END PUBLIC KEY-----\n") + len("-----END PUBLIC KEY-----\n")
                pubkey_pem = buffer[start_idx:end_idx]
                print(f"Received public key for {user}: {pubkey_pem[:50]}...")
                # Clear buffer up to the processed message
                buffer = buffer[end_idx:]
                return pubkey_pem
            elif "[INFO]" in buffer:
                start_idx = buffer.index("[INFO]")
                end_idx = buffer.find("\n", start_idx)
                if end_idx == -1:
                    continue  # Wait for more data
                info_msg = buffer[start_idx:end_idx]
                buffer = buffer[end_idx + 1:]
                append_system(info_msg)
                raise ValueError(f"Server reported: {info_msg}")
            else:
                append_system(f"Ignored unexpected message: {data[:50]}...")
                continue
    except Exception as e:
        append_system(f"Failed to retrieve public key for {user}: {e}")
        raise ValueError(f"Failed to retrieve public key: {e}")

# def request_public_key(user):
#     client.send(f"[GETKEY]{user}".encode())
#     response = client.recv(4096).decode()
#     if response.startswith("[PUBKEYRESP]"):
#         return response[len("[PUBKEYRESP]"):]
#     raise ValueError("Failed to retrieve public key.")

# def send():
#     msg = msg_entry.get().strip()
#     if not msg:
#         return
#     if current_chat is None:
#         append_system("⚠️ Please select a recipient from the left.")
#         return
#     try:
#         from cryptography.hazmat.primitives import padding as sympadding

#         # Get recipient's public key
#         pubkey_pem = request_public_key(current_chat)  # implement this below
#         recipient_key = serialization.load_pem_public_key(pubkey_pem.encode())

#         # Generate AES key
#         aes_key = secrets.token_bytes(32)
#         iv = secrets.token_bytes(16)
#         cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
#         encryptor = cipher.encryptor()

#         # Pad and encrypt message
#         padder = sympadding.PKCS7(128).padder()
#         padded_msg = padder.update(msg.encode()) + padder.finalize()
#         ciphertext = encryptor.update(padded_msg) + encryptor.finalize()

#         # Encrypt AES key with RSA
#         encrypted_key = recipient_key.encrypt(
#             aes_key,
#             padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
#         )

#         # Construct payload: base64(aes_key_rsa)|base64(iv)|base64(ciphertext)
#         payload = f"{current_chat}|{base64.b64encode(encrypted_key).decode()}|{base64.b64encode(iv).decode()}|{base64.b64encode(ciphertext).decode()}"
#         client.send(payload.encode())
        
#         msg_entry.delete(0, tk.END)
#         chat_log[current_chat].append(f"You: {msg}")
#         save_chat_history(chat_log)
#         refresh_chat_display()
#     except:
#         append_system("❌ Message failed to send.")
#         msg_entry.delete(0, tk.END)

def send():
    msg = msg_entry.get().strip()
    if not msg:
        return
    if current_chat is None:
        append_system("⚠️ Please select a recipient from the left.")
        return
    try:
        # Get recipient's public key
        pubkey_pem = request_public_key(current_chat)
        recipient_key = serialization.load_pem_public_key(pubkey_pem.encode())

        # Generate AES key
        aes_key = secrets.token_bytes(32)
        iv = secrets.token_bytes(16)
        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
        encryptor = cipher.encryptor()

        # Pad and encrypt message
        padder = sympadding.PKCS7(128).padder()
        padded_msg = padder.update(msg.encode()) + padder.finalize()
        ciphertext = encryptor.update(padded_msg) + encryptor.finalize()

        # Encrypt AES key with RSA
        encrypted_key = recipient_key.encrypt(
            aes_key,
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
        )

        # Construct payload: base64(aes_key_rsa)|base64(iv)|base64(ciphertext)
        payload = f"{current_chat}|{base64.b64encode(encrypted_key).decode()}|{base64.b64encode(iv).decode()}|{base64.b64encode(ciphertext).decode()}"
        client.send(payload.encode())
        
        msg_entry.delete(0, tk.END)
        chat_log[current_chat].append(f"You: {msg}")
        save_chat_history(chat_log)
        refresh_chat_display()
    except Exception as e:
        append_system(f"❌ Message failed to send: {e}")
        msg_entry.delete(0, tk.END)

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

KEY_DIR = os.path.expanduser("~/.chat_keys")
os.makedirs(KEY_DIR, exist_ok=True)

PRIVATE_KEY_PATH = os.path.join(KEY_DIR, f"{username}_private.pem")
PUBLIC_KEY_PATH = os.path.join(KEY_DIR, f"{username}_public.pem")

if not os.path.exists(PRIVATE_KEY_PATH):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with open(PRIVATE_KEY_PATH, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()))
    with open(PUBLIC_KEY_PATH, "wb") as f:
        f.write(private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo))
else:
    with open(PRIVATE_KEY_PATH, "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)

with open(PUBLIC_KEY_PATH, "rb") as f:
    client.send(b"[PUBKEY]" + f.read())


connected = True

if not os.path.exists(CHAT_HISTORY):
    with open(CHAT_HISTORY, "w") as f:
        json.dump({}, f)
chat_log = load_chat_history()        # {username: [message strings]}
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

# Populate sidebar with past chat users
for user in chat_log:
    add_to_sidebar(user)

# Optionally, load the most recent chat
if chat_log:
    current_chat = list(chat_log.keys())[-1]
    refresh_chat_display()


# === Setup and Start ===
send_btn.config(command=send)
threading.Thread(target=receive, daemon=True).start()
root.mainloop()
