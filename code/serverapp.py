import socket
import threading
import os
import json

clients = {}  # {client_id: conn}
usernames = {}  # {client_id: username}
valid_users = {
}
client_id_counter = 1
lock = threading.Lock()

# USER_DB_FILE = "users.json"

chat_history = {}  # {username: {other_username: [message1, message2, ...]}}
# CHAT_HISTORY_FILE = "chat_history.json"

USER_DB_FILE = os.path.expanduser("~/.chat_users.json")
CHAT_HISTORY_FILE = os.path.expanduser("~/.chat_history.json")


def load_chat_history():
    global chat_history
    if os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "r") as f:
            chat_history = json.load(f)

def save_chat_history():
    with open(CHAT_HISTORY_FILE, "w") as f:
        json.dump(chat_history, f)

def load_users():
    global valid_users
    if os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, "r") as f:
            valid_users = json.load(f)

def save_users():
    with open(USER_DB_FILE, "w") as f:
        json.dump(valid_users, f)

def handle_client(conn, addr, client_id):
    # First receive the username
    # Receive login info
    login_data = conn.recv(1024).decode().strip()
    if "|" not in login_data:
        conn.send("Invalid format".encode())
        conn.close()
        return
    username, password = login_data.split("|", 1)

    # Validate credentials
    if username in valid_users:
        if valid_users[username] != password:
            conn.send("Invalid username or password. New users, choose a different username. Existing users, enter the correct password.".encode())
            conn.close()
            return
        else:
            print(f"[AUTHENTICATED] {username}")
            conn.send("OK".encode())
    else:
        # Auto-register new user
        valid_users[username] = password
        save_users()
        print(f"[REGISTERED] New user: {username}")
        conn.send("OK".encode())

    # Proceed if authenticated
    usernames[client_id] = username
    print(f"[NEW] {username} ({addr}) as Client {client_id}")
    conn.send(f"[INFO] You are Client {client_id} ({username})\n".encode())
    broadcast(f"[INFO] {username} joined the chat.\n", conn)
    
    
    # Send chat history to client
    user_history = chat_history.get(username, {})
    # print(user_history.items())
    for other_user, message_contents in user_history.items():
        for msg_content in message_contents:
            sender = msg_content[0]
            msg = msg_content[1]
            try:
                conn.send(f"[{other_user}][{sender}] {msg}\n".encode())
            except:
                pass
    
    try:
        while True:
            msg = conn.recv(1024).decode()
            if not msg:
                break
            # Format: "to_username|message"
            # print(msg)
            if "|" in msg:
                to_username, content = msg.split("|", 1)
                from_username = usernames[client_id]
                
                # [sender, content]
                content_packet = [from_username, f"{content}\n"]
                
                if to_username not in valid_users:
                    try:
                        conn.send(f"[INFO] ❌ User '{to_username}' does not exist.\n".encode())
                    except:
                        pass
                    continue
                
                send_msg = f"[{from_username}][{from_username}] {content}\n"
                if to_username != from_username:
                    send_to_username(to_username, send_msg)
                
                # Save message to chat history
                chat_history.setdefault(from_username, {}).setdefault(to_username, []).append(content_packet)
                if from_username != to_username:
                    chat_history.setdefault(to_username, {}).setdefault(from_username, []).append(content_packet)
                save_chat_history()
    except:
        pass

    with lock:
        del clients[client_id]
        del usernames[client_id]
    conn.close()
    broadcast(f"[INFO] {username} disconnected.\n", None)
    print(f"[DISCONNECTED] {username}")

def send_to_username(username, msg):
    for cid, uname in usernames.items():
        if uname == username:
            try:
                clients[cid].send(msg.encode())
            except:
                pass

def broadcast(msg, sender_conn):
    for conn in clients.values():
        if conn != sender_conn:
            try:
                conn.send(msg.encode())
            except:
                pass

def send_to_client(client_id, msg):
    conn = clients.get(client_id)
    if conn:
        try:
            conn.send(msg.encode())
        except:
            pass

def start_server(host='0.0.0.0', port=12345):
    global client_id_counter
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    print(f"[LISTENING] on {host}:{port}")

    while True:
        conn, addr = server.accept()
        with lock:
            client_id = client_id_counter
            client_id_counter += 1
            clients[client_id] = conn
        thread = threading.Thread(target=handle_client, args=(conn, addr, client_id))
        thread.start()

if __name__ == "__main__":
    load_users()
    load_chat_history()
    start_server()
