import socket
import threading
from cryptography.fernet import Fernet
import sqlite3

ENCRYPTION_KEY = b'_ElApoJm7Q0aRh95L2c2HNYZtT55nqaL16QkBwD0BD8='
cipher = Fernet(ENCRYPTION_KEY)

class Server:
    def __init__(self, host="0.0.0.0", port=5003, max_clients=3):
        self.host = host
        self.port = port
        self.max_clients = max_clients
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = {}  
        self.lock = threading.Lock()
        self.semaphore = threading.Semaphore(max_clients)
        self.queue_number = 0

        self.db = sqlite3.connect("chat_history.db", check_same_thread=False)
        self.cursor = self.db.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                recipient TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.db.commit()
    
    def start_server(self):
        self.server.bind((self.host, self.port))
        self.server.listen(self.max_clients)
        print(f"[SERVER] Listening on {self.host}:{self.port}")

        while True:
            client_socket, addr = self.server.accept()
            print(f"[SERVER] NEW CONNECTION {addr} connected.")
            thread = threading.Thread(target=self.handle_client, args=(client_socket,))
            thread.start()
    
    def handle_client(self, client_socket):
        try:
            if not self.semaphore.acquire(blocking=False):
                with self.lock:
                    self.queue_number += 1
                msg_wait = f"[SERVER FULL] Please wait while another user disconnects. You are {self.queue_number} in queue"
                client_socket.send(cipher.encrypt(msg_wait.encode("utf-8")))
                self.semaphore.acquire()
                with self.lock:
                    self.queue_number -= 1
                client_socket.send(cipher.encrypt("You have entered. You can chat now".encode("utf-8")))
            
            # Receive username as plain text
            username = client_socket.recv(1024).decode("utf-8").strip()
            if not username:
                client_socket.close()
                return
            
            with self.lock:
                self.clients[username] = client_socket
                print(f"[SERVER] {username} registered")
                client_socket.send(cipher.encrypt("[SERVER TO CLIENT]: You can chat now".encode("utf-8")))
            
            while True:
                encrypt_msg = client_socket.recv(1024)
                if not encrypt_msg:
                    break
                msg = cipher.decrypt(encrypt_msg).decode('utf-8')
                print(f"[CLIENT TO SERVER] Message from {username}: {msg}")
                # If handling file transfers, add logic here
                if "/file" in msg:
                    pass 
                self.route_message(username, msg)
        
        except Exception as error:
            print(f"[SERVER CATCH ERROR] {error}")
        
        finally:
            with self.lock:
                for user, sock in list(self.clients.items()):
                    if sock == client_socket:
                        print(f"[SERVER] {user} disconnected")
                        del self.clients[user]
                        break
            client_socket.close()
            self.semaphore.release()
    
    def route_message(self, sender_username, message):
        recpt_username, msg = message.split(":", 1)
        recpt_username = recpt_username.strip()
        msg = msg.strip()

        insert_query = "INSERT INTO chat_history (sender, recipient, message) VALUES (?, ?, ?)"
        with self.lock:
            self.cursor.execute(insert_query, (sender_username, recpt_username, msg))
            self.db.commit()
        
        with self.lock:
            if recpt_username in self.clients:
                send_msg = f"{sender_username}: {msg}"
                send_msg_encrypt = cipher.encrypt(send_msg.encode("utf-8"))
                self.clients[recpt_username].send(send_msg_encrypt)
            else:
                self.clients[sender_username].send(cipher.encrypt("[SERVER TO CLIENT] User does not exist :(".encode('utf-8')))
    
    def get_chatHistory(self, sender_username, target):
        query = """
                SELECT sender, recipient, message, timestamp FROM chat_history
                WHERE (sender = ? AND recipient = ?) OR (sender = ? AND recipient = ?)
                ORDER BY timestamp ASC
                """
        self.cursor.execute(query, (sender_username, target, target, sender_username))
        rows = self.cursor.fetchall()
        return rows

# Run the server
if __name__ == "__main__":
    server_inst = Server()
    server_inst.start_server()
