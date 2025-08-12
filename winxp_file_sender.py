# WinXP File Sender - Minimal implementation for maximum compatibility
# This application is designed to run on Windows XP and send files
# to a compatible receiver using a simple socket-based protocol.

import socket
import os
import sys
import time
import msvcrt  # Windows-specific module for keyboard input

# Configuration
PORT = 25565
CHUNK_SIZE = 4096  # Smaller chunks for older systems

def clear_screen():
    """Clear the console screen"""
    os.system('cls')

def print_header():
    """Print application header"""
    clear_screen()
    print("=" * 60)
    print("            WinXP File Sender v1.0")
    print("=" * 60)
    print("A minimal file transfer utility for Windows XP")
    print("=" * 60)
    print("")

def print_message(message):
    """Print a status message with timestamp"""
    time_str = time.strftime("%H:%M:%S", time.localtime())
    print("[%s] %s" % (time_str, message))

def get_files_in_directory():
    """Get list of files in current directory (excluding system files)"""
    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    files = []
    
    try:
        for filename in os.listdir(base_dir):
            filepath = os.path.join(base_dir, filename)
            
            # Skip directories, system files and this script
            if (os.path.isfile(filepath) and
                not filename.startswith('.') and
                not filename.endswith('.exe') and
                not filename.endswith('.pyc') and
                not filename.endswith('.dll') and
                filename != 'pyprint-filetransfer-config.json' and
                not filename == os.path.basename(sys.argv[0])):
                
                files.append(filename)
    except Exception as e:
        print_message("Error listing directory: %s" % str(e))
        
    return files

def choose_file():
    """Let user choose a file to send"""
    files = get_files_in_directory()
    
    if not files:
        print_message("No files found in current directory.")
        return None
        
    print("\nAvailable files:")
    print("-" * 60)
    
    for i, filename in enumerate(files):
        file_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), filename)
        file_size = os.path.getsize(file_path)
        print("%2d. %-40s %8d bytes" % (i+1, filename, file_size))
    
    print("-" * 60)
    print("Enter file number to send, or 0 to exit: ", end="")
    
    try:
        choice = int(input())
        if choice == 0:
            return None
        if choice < 1 or choice > len(files):
            print_message("Invalid selection.")
            return None
            
        return files[choice-1]
    except ValueError:
        print_message("Please enter a number.")
        return None
    except Exception as e:
        print_message("Error: %s" % str(e))
        return None

def send_file(filename, server_ip):
    """Send a file to the server using the protocol"""
    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    filepath = os.path.join(base_dir, filename)
    
    if not os.path.exists(filepath):
        print_message("File not found: %s" % filepath)
        return False
    
    filesize = os.path.getsize(filepath)
    if filesize == 0:
        print_message("File is empty: %s" % filename)
        return False
    
    print_message("Preparing to send %s (%d bytes)" % (filename, filesize))
    print_message("Connecting to %s:%d..." % (server_ip, PORT))
    
    # Create socket
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)  # 30 second timeout
        sock.connect((server_ip, PORT))
        
        print_message("Connected successfully.")
        
        # Send filename length (8 bytes)
        print_message("Sending filename information...")
        name_bytes = filename.encode('utf-8')
        name_length = str(len(name_bytes)).zfill(8).encode('ascii')
        sock.sendall(name_length)
        
        # Send filename
        sock.sendall(name_bytes)
        
        # Send file size (16 bytes)
        size_bytes = str(filesize).zfill(16).encode('ascii')
        sock.sendall(size_bytes)
        
        # Send file data in chunks
        print_message("Sending file data...")
        with open(filepath, 'rb') as f:
            bytes_sent = 0
            start_time = time.time()
            
            while bytes_sent < filesize:
                # Read chunk
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                    
                # Send chunk
                sock.sendall(chunk)
                bytes_sent += len(chunk)
                
                # Calculate and show progress
                percent = int(bytes_sent * 100 / filesize)
                elapsed = time.time() - start_time
                speed = bytes_sent / (elapsed if elapsed > 0 else 1)
                
                if bytes_sent % (CHUNK_SIZE * 8) == 0 or bytes_sent == filesize:
                    print_message("Progress: %d%% (%d/%d bytes) - %.1f KB/s" % 
                                 (percent, bytes_sent, filesize, speed/1024))
        
        # Calculate total time
        total_time = time.time() - start_time
        transfer_speed = filesize / (total_time if total_time > 0 else 1)
        
        print_message("File sent successfully!")
        print_message("Transfer complete: %d bytes in %.1f seconds (%.1f KB/s)" % 
                     (filesize, total_time, transfer_speed/1024))
        
        # Create sent folder if it doesn't exist
        sent_dir = os.path.join(base_dir, "sent")
        if not os.path.exists(sent_dir):
            os.makedirs(sent_dir)
        
        # Move file to sent folder
        print_message("Moving file to sent folder...")
        sent_path = os.path.join(sent_dir, filename)
        
        # If file exists in sent folder, add number to filename
        if os.path.exists(sent_path):
            name, ext = os.path.splitext(filename)
            i = 1
            while os.path.exists(os.path.join(sent_dir, "%s_%d%s" % (name, i, ext))):
                i += 1
            sent_path = os.path.join(sent_dir, "%s_%d%s" % (name, i, ext))
        
        # Move the file
        import shutil
        shutil.move(filepath, sent_path)
        print_message("File moved to: %s" % sent_path)
        
        return True
        
    except socket.error as e:
        print_message("Connection error: %s" % str(e))
        return False
    except Exception as e:
        print_message("Error: %s" % str(e))
        return False
    finally:
        if sock:
            try:
                sock.close()
            except:
                pass

def main_menu():
    """Display the main menu and handle user input"""
    while True:
        print_header()
        print("Main Menu:")
        print("1. Send a file")
        print("2. Exit")
        print("\nEnter choice: ", end="")
        
        try:
            choice = int(input())
            
            if choice == 1:
                # Get server IP
                print_header()
                print("Enter the receiver's IP address: ", end="")
                server_ip = input().strip()
                
                if not server_ip:
                    print_message("IP address is required.")
                    time.sleep(2)
                    continue
                
                # Choose and send file
                print_header()
                filename = choose_file()
                if filename:
                    print_header()
                    send_file(filename, server_ip)
                    print("\nPress any key to continue...")
                    msvcrt.getch()
                
            elif choice == 2:
                print_message("Exiting...")
                time.sleep(1)
                break
            else:
                print_message("Invalid choice.")
                time.sleep(1)
                
        except ValueError:
            print_message("Please enter a number.")
            time.sleep(1)
        except Exception as e:
            print_message("Error: %s" % str(e))
            time.sleep(2)

if __name__ == "__main__":
    try:
        main_menu()
    except Exception as e:
        print("Fatal error: %s" % str(e))
        print("\nPress any key to exit...")
        msvcrt.getch()
        sys.exit(1)