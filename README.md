> Last update to `README.md` : 10/24/2024
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
You can find all requirements and installation steps, along with an alternative if the main installation steps don't work, on `REQUIREMENTS.md`.
