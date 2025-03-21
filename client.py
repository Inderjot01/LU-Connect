import socket
import threading
import tkinter as tk
from tkinter import simpledialog
from tkinter.scrolledtext import ScrolledText
from cryptography.fernet import Fernet
import os


ENCRYPTION_KEY = b'_ElApoJm7Q0aRh95L2c2HNYZtT55nqaL16QkBwD0BD8='
cipher = Fernet(ENCRYPTION_KEY)

class Client:
    def __init__(self, host="127.0.0.1", port=5003):
        self.host = host
        self.port = port
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.username = None
        self.activeclients = []
        self.ui = None  # Will be set once ChatUI is created

    def connect(self):
        try:
            self.client.connect((self.host, self.port))
            print("[CLIENT] Connected to server")
        except Exception as e:
            print(f"[CLIENT] Connection error: {e}")

    def send_msg(self, msg):
        try:
            encrypted_msg = cipher.encrypt(msg.encode("utf-8"))
            self.client.send(encrypted_msg)
        except Exception as error:
            print(f"[CLIENT ERROR] {error}")

    def receive_msg(self):
        while True:
            try:
                data = self.client.recv(1024)
                if not data:
                    break
              
                try:
                    msg = cipher.decrypt(data).decode("utf-8")
                    if self.ui:
                        self.ui.after(0, lambda m=msg: self.ui.append_message("Server", m))
                except Exception:
                   
                    print("[CLIENT] Received raw data (likely file data)")
            except Exception as e:
                print(f"[CLIENT RECEIVE ERROR] {e}")
                break

    def send_file(self, filepath):
        """Send a file following the protocol:
           1. Wait for server ack (which tells you to send a 10-digit file size header).
           2. Send the file size (as a 10-digit string).
           3. Send the file data.
        """
        try:
            filesize = os.path.getsize(filepath)
            # Send the file size as a 10-digit number (zero-padded)
            size_str = f"{filesize:010d}"
            self.client.send(size_str.encode("utf-8"))
            # Now, send the file data in binary chunks
            with open(filepath, 'rb') as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    self.client.sendall(chunk)
            print(f"[CLIENT] File '{filepath}' sent successfully.")
        except Exception as e:
            print(f"[CLIENT] Error sending file: {e}")

class ChatUI(tk.Tk):
    def __init__(self, client):
        super().__init__()
        self.client = client
        self.client.ui = self

        self.title("Chat Client")
        self.geometry("800x600")
        self.configure(bg="white")
        
        # Left frame 
        self.left_frame = tk.Frame(self, bg="lightgray", width=200)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.active_label = tk.Label(self.left_frame, text="ACTIVE USERS", bg="lightgray", font=("Arial", 12, "bold"))
        self.active_label.pack(pady=10)
        self.user_listbox = tk.Listbox(self.left_frame, font=("Arial", 12))
        self.user_listbox.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        for user in client.activeclients:
            self.user_listbox.insert(tk.END, user)
        
        # Right frame 
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
        if msg:
            if msg == "/mute":
                self.notifications_muted = True
                self.append_message("System", "Notifications muted.")
            elif msg == "/unmute":
                self.notifications_muted = False
                self.append_message("System", "Notifications unmuted.")
            # Check if the message is a file command
            if msg.startswith("/file"):
                # Expected format: /file <filepath> <recipient>
                parts = msg.split()
                if len(parts) < 3:
                    self.append_message("System", "Invalid file command. Usage: /file <filepath> <recipient>")
                    return
                file_path = parts[1]
                
                self.client.send_msg(msg)
                
                self.after(1000, lambda: self.send_file_wrapper(file_path))
            else:
                self.append_message("You", msg)
                self.client.send_msg(msg)
            self.msg_entry.delete(0, tk.END)
    
    def send_file_wrapper(self, file_path):
        """Wrapper to call client's send_file function."""
        self.client.send_file(file_path)
    
    def append_message(self, sender, msg):
        self.chat_display.config(state="normal")
        self.chat_display.insert(tk.END, f"{sender}: {msg}\n")
        self.chat_display.config(state="disabled")
        self.chat_display.see(tk.END)
        
        if sender != "You" and not self.notifications_muted:
            os.system('afplay /System/Library/Sounds/Ping.aiff')

if __name__ == "__main__":
    client = Client(host="127.0.0.1", port=5003)
    
    root = tk.Tk()
    root.withdraw()
    username = simpledialog.askstring("Username", "Enter your username:")
    
    password = simpledialog.askstring("Password", "Enter your password:")
    root.destroy()
    
    if username:
        client.username = username
        client.connect()
        client.activeclients.append(username)
        client.client.send(username.encode("utf-8"))
        
       
        ui = ChatUI(client)
        threading.Thread(target=client.receive_msg, daemon=True).start()
        ui.mainloop()
        client.client.close()


