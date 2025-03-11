import socket
import threading
from cryptography.fernet import Fernet
import sqlite3
import os

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
        # Chat history database
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
        # User authentication database
        self.auth_db = sqlite3.connect("authentication.db", check_same_thread=False)
        self.auth_cursor = self.auth_db.cursor()
        self.auth_cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                userID INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                password TEXT NOT NULL
            )
        """)
        self.auth_db.commit()
    
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

            # Check if the user exists in the database
            if not self.authentication(username):
                error_msg = "[SERVER] Invalid username. Connection refused. Please try again with valid credentials"
                client_socket.send(cipher.encrypt(error_msg.encode("utf-8")))
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
                msg = cipher.decrypt(encrypt_msg).decode("utf-8")
                print(f"[CLIENT TO SERVER] Message from {username}: {msg}")
                
                # Check for file-transfer command first
                if msg.startswith("/file"):
                    self.handle_send_file(username, msg, client_socket)
                elif msg.startswith("/history"):
                    parts = msg.split(" ", 1)
                    if len(parts) < 2 or not parts[1].strip():
                        error_msg = "[SERVER TO CLIENT] Invalid command. Usage: /history <username>"
                        client_socket.send(cipher.encrypt(error_msg.encode("utf-8")))
                    else:
                        target = parts[1].strip()
                        rows = self.get_chatHistory(username, target)
                        if not rows:
                            response = "[SERVER TO CLIENT] No chat history found."
                        else:
                            response_lines = []
                            for row in rows:
                                # row: (sender, recipient, message, timestamp)
                                response_lines.append(f"{row[3]} - {row[0]} to {row[1]}: {row[2]}")
                            response = "\n".join(response_lines)
                        client_socket.send(cipher.encrypt(response.encode("utf-8")))
                else:
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
        try:
            recpt_username, msg = message.split(":", 1)
            recpt_username = recpt_username.strip()
            msg = msg.strip()
        except ValueError:
            # If the message is not in the expected format
            error_msg = "[SERVER TO CLIENT] Message format error. Use: <recipient>: <message>"
            self.clients[sender_username].send(cipher.encrypt(error_msg.encode("utf-8")))
            return

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
    
    def handle_send_file(self, username, msg, client_socket):
        """
        Expected command format: /file <filepath> <recipient>
        After receiving the command, the server sends an acknowledgment to the client
        so that the client can send the file size (as a 10-character string) and then the file data.
        The file is saved in a folder called "recieved_files" (created if it doesn't exist).
        """
        try:
            parts = msg.split()
            if len(parts) < 3:
                error_msg = "[SERVER TO CLIENT] Invalid file command. Usage: /file <filepath> <recipient>"
                client_socket.send(cipher.encrypt(error_msg.encode("utf-8")))
                return
            
            # Extract the file path and recipient (the command word is parts[0])
            _, file_path, recipient = parts[0], parts[1], parts[2]
            file_name = os.path.basename(file_path)
            folder = "recieved_files"
            if not os.path.exists(folder):
                os.makedirs(folder)
            file_save_path = os.path.join(folder, file_name)
            
            # Inform client to send file data: first send a header with file size
            ack_msg = "[SERVER]: Ready to receive file data. Please send the file size as a 10-digit number."
            client_socket.send(cipher.encrypt(ack_msg.encode("utf-8")))
            
            # Receive the file size (10 bytes expected)
            file_size_data = client_socket.recv(10)
            if not file_size_data:
                error_msg = "[SERVER]: File transfer cancelled. No file size received."
                client_socket.send(cipher.encrypt(error_msg.encode("utf-8")))
                return
            file_size_str = file_size_data.decode("utf-8")
            try:
                file_size = int(file_size_str)
            except ValueError:
                error_msg = "[SERVER]: Invalid file size received."
                client_socket.send(cipher.encrypt(error_msg.encode("utf-8")))
                return
            
            received_size = 0
            with open(file_save_path, 'wb') as f:
                while received_size < file_size:
                    chunk = client_socket.recv(min(4096, file_size - received_size))
                    if not chunk:
                        break
                    f.write(chunk)
                    received_size += len(chunk)
            if received_size == file_size:
                success_msg = f"[SERVER]: File '{file_name}' received successfully and saved to '{file_save_path}'."
            else:
                success_msg = f"[SERVER]: File transfer incomplete. Expected {file_size} bytes, received {received_size} bytes."
            client_socket.send(cipher.encrypt(success_msg.encode("utf-8")))
        except Exception as e:
            error_msg = f"[SERVER]: Error receiving file: {str(e)}"
            client_socket.send(cipher.encrypt(error_msg.encode("utf-8")))
    
    def add_user(self, username, password):
        query = "INSERT INTO users (username, password) VALUES (?, ?)"
        self.auth_cursor.execute(query, (username, password))
        self.auth_db.commit()
        return self.auth_cursor.lastrowid
    
    # Test code (REMOVE IT)
    def print_users(self):
        self.auth_cursor.execute("SELECT * FROM users")
        rows = self.auth_cursor.fetchall()
        print("Users in authentication.db:")
        for row in rows:
            print(row)
    
    def authentication(self, username):
        self.auth_cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
        return self.auth_cursor.fetchone() is not None

# Run the server
if __name__ == "__main__":
    server_inst = Server()
    server_inst.add_user("inder1", "inder")
    server_inst.add_user("inder2", "inder")
    server_inst.add_user("inder3", "inder")
    server_inst.print_users()
    server_inst.start_server()

    

