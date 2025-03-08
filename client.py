import socket
import threading
from cryptography.fernet import Fernet

ENCRYPTION_KEY = b'_ElApoJm7Q0aRh95L2c2HNYZtT55nqaL16QkBwD0BD8='
cipher = Fernet(ENCRYPTION_KEY)

class Client:

    def __init__(self, host="127.0.0.1", port=5002):

        self.host = host
        self.port = port
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.username = None
    
    def start_client(self): 
        try:
            self.client.connect((self.host, self.port))
            print(f"[CLIENT] Connected to server")

            self.signin()

            server_resp = self.client.recv(1024)
            print(f"[SERVER TO CLIENT] {server_resp}")

            thread = threading.Thread(target=self.recv_msg, daemon=True)
            thread.start()

            while True:
                msg = input(">>>")
                if msg == "/exit":
                    break
                encrypt_msg = cipher.encrypt(msg.encode("utf-8"))
                self.client.send(encrypt_msg)
        
        except KeyboardInterrupt:
            print("\n[DISCONNECTED]")
        
        finally:
            self.client.close()
    
    def recv_msg(self):

        while True:
            try:
                encrypt_msg = self.client.recv(1024)
                if not encrypt_msg:
                    break
                msg = cipher.decrypt(encrypt_msg).decode("utf-8")
                print("\n" + msg)
            except Exception as error:
                print("[ERROR]", error)
                break

    def signin(self):
        self.username = input("enter usernmaee:")
        self.client.send(self.username.encode("utf-8"))

client_inst = Client()
client_inst.start_client()


    




        
