import socket
import threading
from cryptography.fernet import Fernet
import sqlite3

ENCRYPTION_KEY = b'_ElApoJm7Q0aRh95L2c2HNYZtT55nqaL16QkBwD0BD8='
cipher = Fernet(ENCRYPTION_KEY)

class server:

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
        print(f"[SERVER] Listeing on {self.host}:{self.port}")

        while True:
            client_socket, addr = self.server.accept()
            print(f"[SERVER] NEW CONNECTION {addr} connected.")
            thread = threading.Thread(target=self.handle_client, args=(client_socket,))
            thread.start()
    
    def handle_client(self, client_socket):

        
        
        #[THREADING]: Handeling join req using semaphore

            if not self.semaphore.acquire(blocking= False): #If not TRUE(When token avail)

                with self.lock:
                    self.queue_number += 1
                
                msg_wait = f"[SERVER FULL] Please wait while another user diconnects. You are {self.queue_number} in queue"
                client_socket.send(msg_wait.encode("utf-8"))

                self.semaphore.acquire()

                with self.lock: #[TODO] I don't think it will work

                    self.queue_number -= 1

        
            


            try:

                username = client_socket.recv(1024)
                
                username = username.decode("utf-8").strip()

                if not username:
                    client_socket.close()
                    return
                
                with self.lock:
                    self.clients[username] = client_socket
                    print(f"[SERVER] {username} registered")
                    client_socket.send("[SERVER TO CLIENT]: You can chat now".encode("utf-8"))
                
                while True:

                    encrypt_msg = client_socket.recv(1024)
                    if not encrypt_msg:
                        break
                    msg = cipher.decrypt(encrypt_msg).decode('utf-8')
                    print(f"[CLIENT TO SERVER] Message from {username}:{msg}")
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

                send_msg = f"{sender_username}:{msg}"
                send_msg_encrypt = cipher.encrypt(send_msg.encode("utf-8"))
                self.clients[recpt_username].send(send_msg_encrypt)
                #print(f"[DEBUG] Inserted message from {sender_username} to {recpt_username}")#DEBUG
            
            else:

                self.clients[sender_username].send("[SERVER TO CLIENT] User does not exist D:".encode('utf-8'))




#Code run

server_inst = server()
server_inst.start_server()

#[TODO] for me :D

'''
- History acessing missing
- Limiting number of user connection  missing and handeling missing
- Show active users missing 
- ...



'''




                





