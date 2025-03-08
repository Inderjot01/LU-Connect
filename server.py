#All the librariers used
import socket
import threading
from cryptography.fernet import Fernet
import sqlite3

ENCRYPTION_KEY = b'_ElApoJm7Q0aRh95L2c2HNYZtT55nqaL16QkBwD0BD8='
cipher = Fernet(ENCRYPTION_KEY)

class server:

    def __init__(self, host="0.0.0.0", port=5002, max_clients=3): #[EDIT]here change host

        self.host = host
        self.port = port
        self.max_clients = max_clients
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #creates a socket between client and server
        self.clients = {}  
        self.lock = threading.Lock()#[THREADING]
        self.semaphore = threading.Semaphore(max_clients)#[THREADING]

        #Sqlite database setup

        self.db = sqlite3.connect("chat_history.db", check_same_thread=False)#[THREADING]: Here we set check_same_thread =False means multiple threads can acess the database -- locks needed
        self.cursor = self.db.cursor()

        #table to store data
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
            thread = threading.Thread(target=self.handle_client, args=(client_socket,)) #[THREADING]
            thread.start()
    
    def handle_client(self, client_socket):
        '''Function details: 
        1. Recive the encrypted username
        2. Decrypt the username 
        3. Add the username to dict with key: Username value: (IP, PORT)
        4. Process request by client and forward the message using forward function
        '''
        with self.semaphore:

            try:

                encrypt_username = client_socket.recv(1024)
                username = cipher.decrypt(encrypt_username)
                username = username.decode("utf-8").strip()

                if not username: #Prevents deadlock 
                    client_socket.close()
                    return
                
                with self.lock(): #[THREADING]: Add client to dict 

                    self.clients[username] = client_socket
                    print(f"[SERVER] {username} registered")
                    client_socket.send("[SERVER TO CLIENT]: You can chat now".encode("utf-8"))
                
                while True:

                    encrypt_msg = client_socket.recv(1024)
                    if not encrypt_msg: #when user terminates terminal
                        break
                    msg = cipher.decrypt(encrypt_msg).decode('utf-8')
                    print(f"[CLIENT TO SERVER] Message from {username}:{msg}")
                    self.route_message(username, msg)
            
            except Exception as error:
                print(f"[SERVER CATCH ERROR] {error}")
            
            finally: #Once user disconnects -- .recv returns b'' 

                with self.lock:

                    for username, socket in self.clients.items(): #[EDIT]

                        if socket == client_socket:
                            print(f"[SERVER] {username} disconnected")
                            del self.clients[username]
                            break

                
                client_socket.close() #here maybe send have function to send a message out that place is there for new user to join?

    def route_message(self, sender_username, message):

        #Here stuff

        recpt_username, msg = message.split(":", 1)
        recpt_username = recpt_username.strip()
        msg = msg.strip()

        #Store the message 
        



                





