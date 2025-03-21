# LU Connect

LU Connect is a real-time client-server chat application built using Python. It supports secure messaging, file transfers, and chat history retrieval. The system follows the Observer Pattern to enable real-time message delivery and efficient client-server communication.

## Features

- User authentication using SQLite
- Real-time encrypted messaging between users
- File transfer support between clients
- Chat history retrieval from the database
- Observer Pattern implementation for client updates
- Multi-threaded server for handling multiple clients
- GUI built with Tkinter

## Technologies Used

- Python 3
- Socket Programming
- Tkinter (GUI)
- SQLite (Database)
- Cryptography (Fernet encryption)

## How to Run

1. Clone the repository:

2. Install required dependencies: pip install cryptography

3. Run the server: python3 server.py

4. Run the client (in a separate terminal or machine): pyhton3 client.py

