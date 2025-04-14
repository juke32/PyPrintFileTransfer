import socket
import os
import sys
import shutil
import time
from datetime import datetime
import threading

# Version 2025-4-14_1455

# Configuration
PORT = 25565
CHUNK_SIZE = 8192  # Smaller chunks for better compatibility
SCAN_INTERVAL = 3  # Seconds between folder scans

def get_timestamp():
    """Get current time formatted as string"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def print_with_timestamp(message):
    """Print a message with timestamp"""
    timestamp = get_timestamp()
    print("[%s] %s" % (timestamp, message))

def send_file(filepath, server_ip, port=PORT):
    """Send a single file to the server"""
    try:
        # Get file info
        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath)
        
        print_with_timestamp("Sending file: %s (%d bytes)" % (filename, filesize))
        print_with_timestamp("Connecting to %s:%d..." % (server_ip, port))
        
        # Create socket with timeout
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)
        
        try:
            # Connect to server
            sock.connect((server_ip, port))
            print_with_timestamp("Connected successfully")
            
            # Send filename length (8 bytes, padded ASCII number)
            name_bytes = filename.encode('utf-8')
            name_length = str(len(name_bytes)).zfill(8).encode('ascii')
            sock.sendall(name_length)
            
            # Send filename
            sock.sendall(name_bytes)
            
            # Send file size (16 bytes, padded ASCII number)
            size_bytes = str(filesize).zfill(16).encode('ascii')
            sock.sendall(size_bytes)
            
            # Send file data in chunks
            bytes_sent = 0
            with open(filepath, 'rb') as f:
                start_time = time.time()
                
                while bytes_sent < filesize:
                    # Read chunk
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    
                    # Send chunk
                    sock.sendall(chunk)
                    bytes_sent += len(chunk)
                    
                    # Show progress occasionally
                    if bytes_sent % (CHUNK_SIZE * 10) == 0 or bytes_sent == filesize:
                        percent = int(bytes_sent * 100 / filesize)
                        print_with_timestamp("Progress: %d%% (%d/%d bytes)" % (percent, bytes_sent, filesize))
                
                # Calculate speed
                elapsed = time.time() - start_time
                speed = filesize / (elapsed if elapsed > 0 else 1)
                print_with_timestamp("File sent successfully! (%.1f KB/s)" % (speed/1024))
            
            print_with_timestamp("Transfer complete")
            
            # Create sent folder if it doesn't exist
            base_dir = os.path.dirname(os.path.abspath(filepath))
            sent_dir = os.path.join(base_dir, "sent")
            if not os.path.exists(sent_dir):
                os.makedirs(sent_dir)
            
            # Move file to sent folder
            sent_path = os.path.join(sent_dir, filename)
            print_with_timestamp("Moving file to sent folder")
            shutil.move(filepath, sent_path)
            
            return True
            
        except socket.error as e:
            print_with_timestamp("Socket error: %s" % str(e))
            return False
        finally:
            sock.close()
            
    except Exception as e:
        print_with_timestamp("Error: %s" % str(e))
        return False

def watch_folder(server_ip, port=PORT):
    """Watch folder for files and send them"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    processed_files = set()  # Track already processed files
    
    try:
        print("\n" + "="*50)
        print("SIMPLE FILE SENDER")
        print("="*50)
        print("\nWatching for files to send to %s:%d" % (server_ip, port))
        print("Place files in this folder to send them automatically")
        print("Files will be moved to 'sent' folder after transfer")
        print("Press Ctrl+C to stop\n")
        
        # Create sent folder if needed
        sent_dir = os.path.join(base_dir, "sent")
        if not os.path.exists(sent_dir):
            os.makedirs(sent_dir)
        
        # Main loop
        while True:
            try:
                # List files in current directory
                files = []
                try:
                    # More efficient way to scan directory
                    with os.scandir(base_dir) as entries:
                        for entry in entries:
                            if entry.is_file() and not entry.name in processed_files:
                                files.append(entry.name)
                except AttributeError:
                    # Fallback for older Python versions
                    files = [f for f in os.listdir(base_dir) 
                           if os.path.isfile(os.path.join(base_dir, f)) 
                           and not f in processed_files]
                
                # Process new files
                for filename in files:
                    filepath = os.path.join(base_dir, filename)
                    
                    # Skip directories, this script, and system files
                    if (not filename.startswith('.') and
                        not filename.endswith('.exe') and
                        not filename.endswith('.pyc') and
                        not filename.endswith('.pyd') and
                        not filename.endswith('.dll') and
                        not filename.endswith('.bat') and
                        not filename.endswith('.log') and
                        filename != os.path.basename(__file__) and
                        not filename == "file_transfer_xp.py"):
                        
                        # Send the file
                        success = send_file(filepath, server_ip, port)
                        
                        # Add to processed files even if sending failed 
                        # to avoid repeated attempts on problem files
                        processed_files.add(filename)
                        
                        # Keep the processed files list manageable
                        if len(processed_files) > 1000:
                            processed_files = set(list(processed_files)[-500:])
                
                # Wait before checking again - increase this value to reduce CPU usage
                time.sleep(SCAN_INTERVAL)
                
            except KeyboardInterrupt:
                print_with_timestamp("Stopping file monitoring")
                break
                
    except Exception as e:
        print_with_timestamp("Error in main loop: %s" % str(e))

def handle_client(client_socket, client_address, received_dir):
    """Handle incoming file transfer from a client"""
    try:
        print_with_timestamp("New connection from %s:%d" % client_address)
        client_socket.settimeout(30)
        
        # Receive filename length (8 bytes)
        name_length_data = client_socket.recv(8)
        if not name_length_data:
            print_with_timestamp("Client disconnected - no filename length received")
            return
            
        try:
            name_length = int(name_length_data.decode('ascii'))
            print_with_timestamp("Filename length: %d bytes" % name_length)
        except (ValueError, UnicodeDecodeError) as e:
            print_with_timestamp("Error decoding filename length: %s" % str(e))
            return
            
        # Receive filename
        filename_data = client_socket.recv(name_length)
        if not filename_data:
            print_with_timestamp("Client disconnected - no filename received")
            return
            
        try:
            filename = filename_data.decode('utf-8')
            print_with_timestamp("Filename: %s" % filename)
        except UnicodeDecodeError as e:
            print_with_timestamp("Error decoding filename: %s" % str(e))
            return
            
        # Receive file size (16 bytes)
        size_data = client_socket.recv(16)
        if not size_data:
            print_with_timestamp("Client disconnected - no file size received")
            return
            
        try:
            file_size = int(size_data.decode('ascii'))
            print_with_timestamp("File size: %d bytes" % file_size)
        except (ValueError, UnicodeDecodeError) as e:
            print_with_timestamp("Error decoding file size: %s" % str(e))
            return
            
        # Prepare file path
        filepath = os.path.join(received_dir, filename)
        if os.path.exists(filepath):
            base, ext = os.path.splitext(filename)
            i = 1
            while os.path.exists(os.path.join(received_dir, "%s_%d%s" % (base, i, ext))):
                i += 1
            filepath = os.path.join(received_dir, "%s_%d%s" % (base, i, ext))
            print_with_timestamp("File already exists - saving as %s" % os.path.basename(filepath))
        
        # Receive file data
        received = 0
        start_time = time.time()
        
        with open(filepath, 'wb') as f:
            while received < file_size:
                # Calculate remaining bytes
                remaining = file_size - received
                # Read chunk (or remaining bytes if smaller)
                chunk = client_socket.recv(min(CHUNK_SIZE, remaining))
                if not chunk:
                    print_with_timestamp("Connection lost during transfer - got %d/%d bytes" % 
                                       (received, file_size))
                    break
                
                # Write chunk and update progress
                f.write(chunk)
                received += len(chunk)
                
                # Show progress occasionally
                if received % (CHUNK_SIZE * 10) == 0 or received == file_size:
                    percent = int(received * 100 / file_size)
                    elapsed = time.time() - start_time
                    speed = received / (elapsed if elapsed > 0 else 1)
                    print_with_timestamp("Progress: %d%% (%d/%d bytes) - %.1f KB/s" % 
                                       (percent, received, file_size, speed/1024))
        
        # Check if transfer was complete
        if received == file_size:
            elapsed = time.time() - start_time
            speed = file_size / (elapsed if elapsed > 0 else 1)
            print_with_timestamp("File received successfully: %s (%.1f KB/s)" % 
                               (os.path.basename(filepath), speed/1024))
        else:
            print_with_timestamp("Incomplete file received: %s (%d of %d bytes)" % 
                               (os.path.basename(filepath), received, file_size))
                
    except Exception as e:
        print_with_timestamp("Error handling client: %s" % str(e))
    finally:
        client_socket.close()

def receive_files(listen_ip=None, port=PORT):
    """Start server to receive files"""
    try:
        # Create received directory if needed
        base_dir = os.path.dirname(os.path.abspath(__file__))
        received_dir = os.path.join(base_dir, "received")
        if not os.path.exists(received_dir):
            os.makedirs(received_dir)
        
        # Create server socket
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bind to address
        ip = listen_ip or ''  # Empty string means listen on all interfaces
        server.bind((ip, port))
        server.listen(5)
        server.settimeout(1)  # Allow keyboard interrupt to work
        
        print("\n" + "="*50)
        print("FILE RECEIVER")
        print("="*50)
        print("\nListening for incoming files on %s:%d" % (ip or '*', port))
        print("Received files will be saved to: %s" % received_dir)
        print("Press Ctrl+C to stop\n")
        
        # Accept connections until interrupted
        while True:
            try:
                # Accept connection with timeout
                client, addr = server.accept()
                
                # Handle client in a separate thread
                handler = threading.Thread(target=handle_client, 
                                          args=(client, addr, received_dir))
                handler.daemon = True
                handler.start()
                
            except socket.timeout:
                # This is expected - it allows the loop to check for keyboard interrupt
                continue
            except KeyboardInterrupt:
                print_with_timestamp("Server stopping...")
                break
            except Exception as e:
                print_with_timestamp("Error accepting connection: %s" % str(e))
                time.sleep(1)
                
    except Exception as e:
        print_with_timestamp("Server error: %s" % str(e))
    finally:
        try:
            server.close()
        except:
            pass
        print_with_timestamp("Server stopped")

# Python 2 compatible input function that always returns a string
def get_input(prompt):
    """Get user input as string, compatible with both Python 2 and 3"""
    if sys.version_info[0] >= 3:
        return input(prompt)
    else:
        return raw_input(prompt)

# Main program entry point
if __name__ == "__main__":
    try:
        # Clear screen for better readability
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("\n" + "="*50)
        print("SIMPLE FILE TRANSFER TOOL")
        print("="*50)
        print("\nWhat would you like to do?")
        print("1. Send files")
        print("2. Receive files")
        
        choice = get_input("\nEnter your choice (1 or 2): ").strip()
        
        if choice == "1":
            # Sending files
            # Get IP address from command line or via safe input
            if len(sys.argv) > 1:
                server_ip = sys.argv[1]
            else:
                # Use the safe input function
                print("\nEnter the IP address of the receiver computer:")
                server_ip = get_input("IP Address: ").strip()
            
            # Parse IP and port if provided in format IP:PORT
            port = PORT  # Default port
            if server_ip and ":" in server_ip:
                try:
                    parts = server_ip.split(":")
                    ip_part = parts[0]
                    port_part = parts[1]
                    
                    # Try to convert port to integer
                    port = int(port_part)
                    server_ip = ip_part
                    print("Using custom port: %d" % port)
                except:
                    print("Invalid port format. Using default port: %d" % PORT)
            
            # Start the file watcher if we have an IP
            if server_ip:
                watch_folder(server_ip, port)
            else:
                print("Error: IP address is required")
                
        elif choice == "2":
            # Receiving files
            print("\nHow would you like to listen?")
            print("1. Listen on all network interfaces (recommended)")
            print("2. Listen on a specific IP address")
            
            listen_choice = get_input("\nEnter your choice (1 or 2): ").strip()
            
            listen_ip = None
            if listen_choice == "2":
                print("\nEnter the IP address to listen on:")
                listen_ip = get_input("IP Address: ").strip()
                
            # Get custom port if needed
            use_custom_port = get_input("\nUse default port (%d)? (y/n): " % PORT).strip().lower()
            if use_custom_port == 'n':
                try:
                    port = int(get_input("Enter port number: ").strip())
                except:
                    print("Invalid port number. Using default port: %d" % PORT)
                    port = PORT
            else:
                port = PORT
                
            # Start the receiver
            receive_files(listen_ip, port)
            
        else:
            print("Invalid choice.")
            
    except KeyboardInterrupt:
        print("\nProgram stopped by user")
    except Exception as e:
        print("\nError: %s" % str(e))
    
    print("\nPress Enter to exit...")
    get_input("")
