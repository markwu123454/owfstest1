# C2 Server Project

This Command and Control (C2) server manages communication between a controller and multiple clients using WebSockets. The server allows controllers to issue commands to clients and receive responses in real-time. This project is for educational purposes only.

## Overview
- **Controller**: Issues commands to clients, requests client lists, and monitors client responses.
- **Clients**: Receives commands from the controller, executes them, and sends back responses.

## Features
- **Real-time WebSocket communication**: Facilitates live command and response exchanges between the controller and clients.
- **Unique ID assignment for clients**: Each client is assigned a unique identifier for tracking and communication.
- **Command issuance and response relay**: Controllers can issue commands to specific clients and receive their responses.
- **24-hour message retention with automatic cleanup**: Messages are stored for 24 hours and old messages are automatically removed to maintain performance.
- **JSON-based logging**: Logs all connections, commands, and responses in a structured JSON format for easier debugging and tracking.

## Requirements
- **Python 3.8+**: Ensure Python 3.8 or higher is installed.
- Install dependencies with:
  ```sh
  pip install -r requirements.txt
  ```

### Libraries
- **asyncio**: Used for handling asynchronous I/O operations.
- **websockets**: Implements the WebSocket protocol for real-time communication.
- **uuid**: Generates unique IDs for clients.
- **json**: Handles JSON encoding and decoding for message transmission.
- **logging**: Manages server-side logging of activities.
- **socket**: Provides network interface functions to determine local IP.
- **datetime**: Used for handling timestamps and message retention.

