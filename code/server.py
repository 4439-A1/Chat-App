import socket
import threading

clients = {}  # {client_id: conn}
usernames = {}  # {client_id: username}
valid_users = {
}
client_id_counter = 1
lock = threading.Lock()

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
            conn.send("Invalid username or password".encode())
            conn.close()
            return
        # else:
        #     conn.send("OK".encode())
    else:
        # Auto-register new user
        valid_users[username] = password
        print(f"[REGISTERED] New user: {username}")
        # conn.send("OK".encode())

    # Proceed if authenticated
    conn.send("OK\n".encode())
    usernames[client_id] = username
    print(f"[NEW] {username} ({addr}) as Client {client_id}")
    conn.send(f"[INFO] You are Client {client_id} ({username})".encode())
    broadcast(f"[INFO] {username} joined the chat.", conn)
    # print(f"[NEW] {username} ({addr}) as Client {client_id}")
    # conn.send(f"[INFO] You are Client {client_id} ({username})".encode())
    # broadcast(f"[INFO] {username} joined the chat.", conn)

    try:
        while True:
            msg = conn.recv(1024).decode()
            if not msg:
                break
            # Format: "to_username|message"
            if "|" in msg:
                to_username, content = msg.split("|", 1)
                from_username = usernames[client_id]
                send_to_username(to_username, f"[{from_username}] {content}")
    except:
        pass

    with lock:
        del clients[client_id]
        del usernames[client_id]
    conn.close()
    broadcast(f"[INFO] {username} disconnected.", None)
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
    start_server()
