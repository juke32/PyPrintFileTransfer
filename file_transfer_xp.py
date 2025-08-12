import socket
import os
import sys
import shutil
import json
import time
from datetime import datetime

# Optional Windows APIs for printing
try:
    import win32api  # type: ignore
    import win32print  # type: ignore
except Exception:
    win32api = None  # type: ignore
    win32print = None  # type: ignore

# Basic configuration (will be overridden by config file if present)
CONFIG = {
    "port": 25565,
    "printer_name": "No Printer",
    "print_filetypes": [".pdf", ".png"],
}
PORT = CONFIG["port"]
CHUNK_SIZE = 8192  # Smaller chunks for compatibility

def get_application_path():
    return os.path.dirname(os.path.abspath(sys.argv[0]))

def get_config_path():
    return os.path.join(get_application_path(), "pyprint-filetransfer-config.json")

def load_config():
    global CONFIG, PORT
    try:
        cfg_path = get_config_path()
        if os.path.exists(cfg_path):
            f = open(cfg_path, 'r')
            try:
                data = json.load(f)
            finally:
                f.close()
            # merge known keys only
            for k in list(CONFIG.keys()):
                if k in data:
                    CONFIG[k] = data[k]
            # normalize extensions
            if isinstance(CONFIG.get("print_filetypes"), list):
                CONFIG["print_filetypes"] = [
                    (ft if str(ft).startswith('.') else ('.' + str(ft))).lower()
                    for ft in CONFIG["print_filetypes"]
                ]
            PORT = int(CONFIG.get("port", 25565))
            log("Loaded config from %s" % cfg_path)
    except Exception as e:
        log("Warning: failed to load config: %s" % str(e))

def print_file(filepath):
    try:
        printer_name = CONFIG.get("printer_name", "No Printer")
        if not printer_name or printer_name == "No Printer":
            return

        # Default printer
        if printer_name == "Default Printer":
            try:
                os.startfile(filepath, "print")
                log("Sent %s to default printer" % os.path.basename(filepath))
                return
            except Exception as e:
                log("Default print failed, trying printto: %s" % str(e))

        # Specific printer via ShellExecute 'printto'
        if win32api is not None:
            try:
                win32api.ShellExecute(0, 'printto', filepath, '"%s"' % printer_name, '.', 0)  # type: ignore
                log("Sent %s to printer '%s'" % (os.path.basename(filepath), printer_name))
                return
            except Exception as e:
                log("printto failed: %s" % str(e))

        # Fallback: temporarily set default and use startfile
        if win32print is not None:
            try:
                current = None
                try:
                    current = win32print.GetDefaultPrinter()  # type: ignore
                except Exception:
                    current = None
                try:
                    win32print.SetDefaultPrinter(printer_name)  # type: ignore
                    os.startfile(filepath, "print")
                    log("Printed %s via temporary default '%s'" % (os.path.basename(filepath), printer_name))
                finally:
                    try:
                        if current:
                            win32print.SetDefaultPrinter(current)  # type: ignore
                    except Exception:
                        pass
            except Exception as e:
                log("Temp default print failed: %s" % str(e))
    except Exception as e:
        log("Error printing file: %s" % str(e))

def log(message):
    """Write message to log and console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = "[%s] %s" % (timestamp, message)
    print(log_message)
    try:
        with open("file_transfer.log", "a") as f:
            f.write(log_message + "\n")
    except:
        pass

def send_mode(server_ip):
    """Client mode - watch for files and send them"""
    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    sent_dir = os.path.join(base_dir, "sent")
    
    # Create sent folder if it doesn't exist
    if not os.path.exists(sent_dir):
        try:
            os.makedirs(sent_dir)
        except Exception as e:
            log("Error creating sent directory: %s" % str(e))
            return
    
    log("Running in SEND mode - watching for files to send to %s:%d" % (server_ip, PORT))
    log("Press Ctrl+C to stop")
    
    # Main loop - watch directory for files
    try:
        while True:
            try:
                # Get list of files in current directory
                files = os.listdir(base_dir)
                for filename in files:
                    # Full path to file
                    filepath = os.path.join(base_dir, filename)
                    
                    # Skip directories, hidden files, and special files
                    if (os.path.isfile(filepath) and
                        not filename.startswith('.') and
                        not filename.endswith('.exe') and
                        not filename.endswith('.pyc') and
                        not filename.endswith('.pyd') and
                        not filename.endswith('.dll') and
                        filename != 'pyprint-filetransfer-config.json' and
                        not filename.endswith('.log') and
                        not filename == os.path.basename(sys.argv[0])):
                        
                        # Process the file
                        try:
                            # Get file size
                            file_size = os.path.getsize(filepath)
                            
                            # Skip empty files
                            if file_size == 0:
                                log("Skipping empty file: %s" % filename)
                                continue
                                
                            # Connect to server
                            log("Sending file: %s (%d bytes)" % (filename, file_size))
                            log("Connecting to %s:%d..." % (server_ip, PORT))
                            
                            # Create socket
                            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            s.settimeout(30)  # 30 second timeout
                            
                            try:
                                # Connect to server
                                s.connect((server_ip, PORT))
                                
                                # Send filename length (8 bytes)
                                name_bytes = filename.encode('utf-8')
                                name_len = str(len(name_bytes)).zfill(8).encode('ascii')
                                s.sendall(name_len)
                                
                                # Send filename
                                s.sendall(name_bytes)
                                
                                # Send file size (16 bytes)
                                size_str = str(file_size).zfill(16).encode('ascii')
                                s.sendall(size_str)
                                
                                # Send file data in chunks
                                with open(filepath, 'rb') as f:
                                    bytes_sent = 0
                                    while bytes_sent < file_size:
                                        chunk = f.read(CHUNK_SIZE)
                                        if not chunk:
                                            break
                                        s.sendall(chunk)
                                        bytes_sent += len(chunk)
                                        
                                # Successful transfer
                                log("Successfully sent %s (%d bytes)" % (filename, bytes_sent))
                                
                                # Move file to sent folder
                                dest_path = os.path.join(sent_dir, filename)
                                log("Moving file to sent folder")
                                shutil.move(filepath, dest_path)
                                log("File moved to: %s" % dest_path)
                                
                            except socket.error as e:
                                log("Socket error: %s" % str(e))
                            finally:
                                s.close()
                                
                        except Exception as e:
                            log("Error processing file %s: %s" % (filename, str(e)))
                            
                # Wait before checking for new files
                time.sleep(1)
                
            except KeyboardInterrupt:
                log("Stopping file monitoring")
                break
            except Exception as e:
                log("Error in main loop: %s" % str(e))
                time.sleep(5)  # Longer delay on error
                
    except Exception as e:
        log("Fatal error: %s" % str(e))

def receive_mode(listen_ip=None):
    """Server mode - listen for connections and receive files"""
    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    received_dir = os.path.join(base_dir, "received")
    
    # Create received folder if it doesn't exist
    if not os.path.exists(received_dir):
        try:
            os.makedirs(received_dir)
        except Exception as e:
            log("Error creating received directory: %s" % str(e))
            return
    
    # Create server socket
    server = None
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bind to specified or all interfaces
        ip = listen_ip or ''
        server.bind((ip, PORT))
        server.listen(5)
        
        log("Running in RECEIVE mode - listening on %s:%d" % (ip or '*', PORT))
        log("Files will be saved to: %s" % received_dir)
        log("Press Ctrl+C to stop")
        
        # Main server loop
        while True:
            try:
                # Accept connection
                client, addr = server.accept()
                log("Connection from: %s:%d" % addr)
                
                try:
                    # Set timeout
                    client.settimeout(30)
                    
                    # Get filename length
                    name_len_data = client.recv(8)
                    if not name_len_data:
                        log("Client disconnected")
                        client.close()
                        continue
                    
                    # Parse filename length
                    try:
                        name_len = int(name_len_data.decode('ascii'))
                    except:
                        log("Invalid filename length received")
                        client.close()
                        continue
                    
                    # Get filename
                    name_data = client.recv(name_len)
                    if not name_data:
                        log("No filename received")
                        client.close()
                        continue
                    
                    # Parse filename
                    try:
                        filename = name_data.decode('utf-8')
                    except:
                        log("Invalid filename received")
                        client.close()
                        continue
                    
                    # Get file size
                    size_data = client.recv(16)
                    if not size_data:
                        log("No file size received")
                        client.close()
                        continue
                    
                    # Parse file size
                    try:
                        file_size = int(size_data.decode('ascii'))
                    except:
                        log("Invalid file size received")
                        client.close()
                        continue
                    
                    # Prepare output file
                    log("Receiving file: %s (%d bytes)" % (filename, file_size))
                    output_path = os.path.join(received_dir, filename)
                    
                    # Receive file data
                    try:
                        received = 0
                        with open(output_path, 'wb') as f:
                            while received < file_size:
                                # Calculate remaining bytes
                                remaining = file_size - received
                                # Read chunk (or remaining bytes if smaller)
                                chunk = client.recv(min(CHUNK_SIZE, remaining))
                                if not chunk:
                                    log("Connection lost during transfer")
                                    break
                                # Write chunk
                                f.write(chunk)
                                received += len(chunk)
                                
                        # Check if transfer was complete
                        if received == file_size:
                            log("Successfully received file: %s (%d bytes)" % (filename, received))
                            # Auto-print if configured and extension allowed
                            try:
                                ext = os.path.splitext(output_path)[1].lower()
                                ftypes = set(CONFIG.get("print_filetypes", [".pdf", ".png"]))
                                if CONFIG.get("printer_name", "No Printer") != "No Printer" and ext in ftypes:
                                    print_file(output_path)
                            except Exception as e:
                                log("Auto print failed: %s" % str(e))
                        else:
                            log("Incomplete file received: %s (%d of %d bytes)" % 
                                (filename, received, file_size))
                    except Exception as e:
                        log("Error saving file: %s" % str(e))
                        
                except Exception as e:
                    log("Error handling client: %s" % str(e))
                finally:
                    client.close()
                    
            except KeyboardInterrupt:
                log("Server stopping")
                break
            except Exception as e:
                log("Server error: %s" % str(e))
                
    except Exception as e:
        log("Fatal server error: %s" % str(e))
    finally:
        try:
            if server:
                server.close()
        except:
            pass
        log("Server stopped")

def print_help():
    print("\nWindows XP File Transfer Utility")
    print("===============================\n")
    print("Usage:")
    print("  As receiver: %s receive [ip_to_listen_on]" % os.path.basename(sys.argv[0]))
    print("  As sender:   %s send server_ip" % os.path.basename(sys.argv[0]))
    print("\nExamples:")
    print("  %s receive" % os.path.basename(sys.argv[0]))
    print("  %s receive 192.168.1.100" % os.path.basename(sys.argv[0]))
    print("  %s send 192.168.1.100\n" % os.path.basename(sys.argv[0]))

if __name__ == "__main__":
    try:
        load_config()
        # No args = print help
        if len(sys.argv) < 2:
            print_help()
            sys.exit(1)

        # Get mode
        mode = sys.argv[1].lower()

        # Process based on mode
        if mode == "receive":
            # Get listen IP if provided
            listen_ip = sys.argv[2] if len(sys.argv) > 2 else None
            receive_mode(listen_ip)
        elif mode == "send":
            # Must provide server IP
            if len(sys.argv) < 3:
                print("Error: Server IP address required for send mode")
                print_help()
                sys.exit(1)
            send_mode(sys.argv[2])
        elif mode in ("-h", "--help", "help"):
            print_help()
        else:
            print("Error: Unknown mode '%s'" % mode)
            print_help()
            sys.exit(1)
    except Exception as e:
        print("Error: %s" % str(e))
        sys.exit(1)