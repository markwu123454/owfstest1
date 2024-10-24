# C2 test

This script is an asynchronous server application that uses Python's `asyncio` and `websockets` libraries to facilitate communication between a controller and multiple connected clients (infected laptops). The key features include registering clients, relaying messages between controllers and infected clients, maintaining a list of connected clients, and cleaning up old messages. This is to test how a C2 network would operate for educational / hobbyist purposes.

### Key Features

- **Asynchronous Communication**: Uses `asyncio` and `websockets` for handling multiple client connections concurrently.
- **JSON Message Handling**: Implements message serialization and deserialization using the `json` library.
- **Client Registration**: Assigns a unique ID to each client and stores relevant details such as role, last seen time, and WebSocket connection.
- **Command Relay**: Controllers can send commands to infected clients, and the server relays the responses back to the controllers.
- **Logging**: Uses the `logging` library along with `jsonlogger` to provide detailed logging for various server activities, formatted as JSON.
- **Message Cleanup**: Old messages are automatically cleaned up after a retention period of 1 day.

### Dependencies

The script requires the following Python libraries:

- `asyncio`: For asynchronous operations and managing concurrent tasks.
- `websockets`: To handle WebSocket communication between clients and the server.
- `json`: For serialization and deserialization of messages.
- `uuid`: To generate unique identifiers for each client connection and command.
- `logging` and `pythonjsonlogger`: For detailed logging, including log messages formatted as JSON.
- `socket`: To determine the local IP address of the server.
- `datetime` and `timedelta`: For managing message timestamps and retention.

### How to Run

1. Install the required dependencies using pip:

   ```sh
   pip install websockets python-json-logger
   ```

2. Run the script:

   ```sh
   python script_name.py
   ```

   Replace `script_name.py` with the actual name of the script file.

### Configuration

- **Logging**: The script uses JSON formatting for logging to make it easy to integrate with log analysis tools.
- **Message Retention**: Messages are retained for 1 day (`MESSAGE_RETENTION_PERIOD = timedelta(days=1)`). This can be configured by modifying the `MESSAGE_RETENTION_PERIOD` variable.
- **WebSocket Server**: The server listens on all available interfaces (`0.0.0.0`) on port `6857`. You can modify the `ip_address` and `port` variables in the `main()` function if needed.

### Functions Overview

- **`cleanup_old_messages()`**: Cleans up messages that are older than the defined retention period.
- **`register_client(websocket, role, client_id, data=None)`**: Registers a new client connection and stores relevant information.
- **`relay_messages(websocket, client_id, role)`**: Handles message relay between controllers and infected clients.
- **`connection_handler(websocket, path)`**: Manages new connections and registers clients.
- **`get_local_ip()`**: Determines the local IP address of the server for logging purposes.
- **`main()`**: Initializes and starts the WebSocket server.

### Logging

The script uses a JSON-based logging format to capture detailed information such as:

- Client registration and disconnections.
- Commands sent from controllers to infected clients.
- Responses received from infected clients.
- Any exceptions that occur during server operation.

The log messages include the client ID, role, and other relevant information to aid in troubleshooting and auditing.

### Use Cases / Purpose

- **Command and Control (C2) Networks**: This script can be used to simulate a basic Command and Control (C2) network. A C2 network is a central component used by attackers to control compromised systems, often called bots or infected clients, and send commands to them. In a C2 scenario, a controller sends instructions to the infected clients and receives responses. This script demonstrates the fundamental operation of such a network, allowing for an understanding of how attackers remotely control multiple devices. It is particularly useful for understanding the flow of data between the control server and infected clients, and for studying how attackers manage a distributed network of compromised systems.
- **Ethical Hacking and Penetration Testing**: This script can be used in controlled environments to simulate an attack scenario where a controller needs to manage and communicate with multiple compromised devices. It can help ethical hackers understand command-and-control (C2) frameworks, their operations, and methods for managing compromised systems.
- **Education and Training**: Network security professionals and students can use this script to understand the communication protocols and interactions in a simulated botnet environment, providing insight into how malicious actors control compromised machines.
- **Proof of Concept for Security Tools**: This script can be used to create proof-of-concept implementations for security tools that detect, block, or monitor command-and-control traffic.

### Future Improvements

- **Authentication**: Implement an authentication mechanism to ensure that only authorized clients can connect and interact with the server.
- **Encryption**: Add support for encrypted WebSocket connections (WSS) to protect data during transmission.
- **Scalability**: Modify the server to handle a larger number of clients by optimizing memory usage and message handling.

### Disclaimer
- **This project is provided for educational purposes only. The use of this server and any associated code is at your own risk. By using this repository, you acknowledge that:

- **Security & Privacy:** This server is not guaranteed to be secure. You should not use it to handle sensitive data or in production environments without proper security audits and implementations.

- **Legal Use:** It is your responsibility to ensure that your use of this server and any of its components complies with applicable laws and regulations in your country. The repository's creator(s) are not responsible for any misuse or illegal activity arising from the use of this code.

- **Support & Maintenance:** This code is provided "as is" without any guarantee of support or future updates. If you encounter issues, feel free to open an issue or contribute to the project, but there are no obligations for further development.
