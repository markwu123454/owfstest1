> Last update to REQUIREMENTS.md : Oct 24, 2024
# Requirements

This project requires Python 3.8 or higher and the following dependencies:

## Installing Dependencies

To install all dependencies, use the provided `requirements.txt` file:

```sh
pip install -r requirements.txt
```

If installing dependencies via `requirements.txt` does not work, you can manually install the required libraries:

```sh
pip install asyncio websockets uuid jsonlogger
```

### Libraries
- **asyncio**: Used for handling asynchronous I/O operations.
- **websockets**: Implements the WebSocket protocol for real-time communication.
- **uuid**: Generates unique IDs for clients.
- **json**: Handles JSON encoding and decoding for message transmission.
- **logging**: Manages server-side logging of activities.
- **socket**: Provides network interface functions to determine local IP.
- **datetime**: Used for handling timestamps and message retention.

Additional standard libraries such as `uuid`, `json`, `logging`, `socket`, and `datetime` are included with Python by default.

