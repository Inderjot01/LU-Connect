import socket
import threading
import tkinter as tk
from tkinter import simpledialog
from tkinter.scrolledtext import ScrolledText
from cryptography.fernet import Fernet
from server import server

ENCRYPTION_KEY = b'_ElApoJm7Q0aRh95L2c2HNYZtT55nqaL16QkBwD0BD8='
cipher = Fernet(ENCRYPTION_KEY)

class Client:
    def __init__(self, host="0.0.0.0", port=5003, max_clients=3):
        self.host = host
        self.port = port
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.username = None
    
    def connection(self):
        self.client.connect((self.host, self.port))
        print(f"[CLIENT] Connected to server")

    def send_msg(self, msg):
        try:
            encrypt_msg = cipher.encrypt(msg.encode("utf-8"))
            self.client.send(encrypt_msg)
        except Exception as error:
            print(f"[CLIENT CATCH ERROR] {error}")
    
    def recev_msg(self):
        global run
        while True:
            try:
                data = self.client.recv(1024)
                if not data:
                    break
                msg = cipher.decrypt(data).decode("utf-8")
                run.after(0, lambda: run.append_message("Server", msg))
            except Exception as error:
                print(f"[ERROR CATCH CLIENT] {error}")
                break

    def close(self):
        pass

class ChatUI(tk.Tk):
    def __init__(self, client):
        super().__init__()
        self.client = client
        self.title("Chat Client")
        self.geometry("800x600")
        self.configure(bg="white")
        
        self.left_frame = tk.Frame(self, bg="lightgray", width=200)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.active_label = tk.Label(self.left_frame, text="ACTIVE USERS", bg="lightgray", font=("Arial", 12, "bold"))
        self.active_label.pack(pady=10)
        self.user_listbox = tk.Listbox(self.left_frame, font=("Arial", 12))
        self.user_listbox.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        for user in list(server_instance.clients.keys()):
            self.user_listbox.insert(tk.END, user)
        
        self.right_frame = tk.Frame(self, bg="white")
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.chat_display = ScrolledText(self.right_frame, font=("Arial", 12), bg="white", fg="black", state="disabled")
        self.chat_display.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        self.input_frame = tk.Frame(self.right_frame, bg="white")
        self.input_frame.pack(fill=tk.X, padx=10, pady=10)
        self.msg_entry = tk.Entry(self.input_frame, font=("Arial", 12))
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,10))
        self.send_button = tk.Button(self.input_frame, text="SEND", font=("Arial", 12), command=self.send)
        self.send_button.pack(side=tk.RIGHT)

    def send(self):
        msg = self.msg_entry.get()
        self.append_message("You", msg)
        self.client.send_msg(msg)
        self.msg_entry.delete(0, tk.END)
    
    def append_message(self, sender, msg):
        self.chat_display.config(state="normal")
        self.chat_display.insert(tk.END, f"{sender}: {msg}\n")
        self.chat_display.config(state="disabled")
        self.chat_display.see(tk.END)
    
    def recv(self):
        threading.Thread(target=self.client.recev_msg, daemon=True).start()

server_instance = server()
client_inst = Client()

root = tk.Tk()
root.withdraw()
username = simpledialog.askstring("Username", "Enter your username:")
root.destroy() 

if username:
    client_inst.username = username
    client_inst.connection()
    client_inst.client.send(username.encode("utf-8"))
    welcome = client_inst.client.recv(1024).decode("utf-8")
    print("[SERVER]:", welcome)
    
    run = ChatUI(client_inst)
    threading.Thread(target=client_inst.recev_msg, daemon=True).start()
    run.mainloop()
    client_inst.close()



    






    
        