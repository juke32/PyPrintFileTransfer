import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import socket
import threading
import os
import shutil
from datetime import datetime
import sys

class FileTransferGUI(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title("File Transfer Application")
        self.geometry("800x600")
        
        # Create directories
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.sent_dir = os.path.join(self.base_dir, "sent")
        self.received_dir = os.path.join(self.base_dir, "received")
        for directory in [self.sent_dir, self.received_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
        
        # Initialize network variables
        self.server_socket = None
        self.is_listening = False
        
        self.create_gui()
    
    def create_gui(self):
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill='both', padx=5, pady=5)
        
        # Create tabs
        self.client_frame = ttk.Frame(self.notebook)
        self.host_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.client_frame, text='Client')
        self.notebook.add(self.host_frame, text='Host')
        
        self.setup_client_tab()
        self.setup_host_tab()
    
    def setup_client_tab(self):
        # Network Settings
        net_frame = ttk.LabelFrame(self.client_frame, text="Connection Settings")
        net_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(net_frame, text="Server IP:").grid(row=0, column=0, padx=5, pady=5)
        self.server_ip = ttk.Entry(net_frame)
        self.server_ip.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(net_frame, text="Port:").grid(row=0, column=2, padx=5, pady=5)
        self.server_port = ttk.Entry(net_frame, width=10)
        self.server_port.insert(0, "25565")
        self.server_port.grid(row=0, column=3, padx=5, pady=5)
        
        # Status
        status_frame = ttk.LabelFrame(self.client_frame, text="Status")
        status_frame.pack(fill="x", padx=5, pady=5)
        self.status_label = ttk.Label(status_frame, text="Ready")
        self.status_label.pack(padx=5, pady=5)
        
        # Log
        log_frame = ttk.LabelFrame(self.client_frame, text="Activity Log")
        log_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15)
        self.log_text.pack(fill="both", expand=True)
    
    def setup_host_tab(self):
        # Network Settings
        net_frame = ttk.LabelFrame(self.host_frame, text="Server Settings")
        net_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(net_frame, text="Listen IP:").grid(row=0, column=0, padx=5, pady=5)
        self.listen_ip = ttk.Combobox(net_frame, values=self.get_local_ips())
        self.listen_ip.grid(row=0, column=1, padx=5, pady=5)
        if self.listen_ip["values"]:
            self.listen_ip.set(self.listen_ip["values"][0])
        
        ttk.Label(net_frame, text="Port:").grid(row=0, column=2, padx=5, pady=5)
        self.listen_port = ttk.Entry(net_frame, width=10)
        self.listen_port.insert(0, "25565")
        self.listen_port.grid(row=0, column=3, padx=5, pady=5)
        
        self.start_btn = ttk.Button(net_frame, text="Start Server", command=self.toggle_server)
        self.start_btn.grid(row=0, column=4, padx=5, pady=5)
        
        # Status
        status_frame = ttk.LabelFrame(self.host_frame, text="Server Status")
        status_frame.pack(fill="x", padx=5, pady=5)
        self.host_status_label = ttk.Label(status_frame, text="Server: Stopped")
        self.host_status_label.pack(padx=5, pady=5)
        
        # Log
        log_frame = ttk.LabelFrame(self.host_frame, text="Server Log")
        log_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.host_log_text = scrolledtext.ScrolledText(log_frame, height=15)
        self.host_log_text.pack(fill="both", expand=True)
    
    def get_local_ips(self):
        try:
            hostname = socket.gethostname()
            ips = []
            # Get primary IP
            try:
                ips.append(socket.gethostbyname(hostname))
            except:
                pass
            
            # Try to get additional IPs
            try:
                for ip in socket.gethostbyname_ex(hostname)[2]:
                    if ip not in ips and not ip.startswith('127.'):
                        ips.append(ip)
            except:
                pass
            
            return ips or ['127.0.0.1']
        except:
            return ['127.0.0.1']
    
    def toggle_server(self):
        if not self.is_listening:
            try:
                ip = self.listen_ip.get()
                port = int(self.listen_port.get())
                
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                
                try:
                    self.server_socket.bind((ip, port))
                    self.server_socket.listen(5)
                    
                    self.is_listening = True
                    self.start_btn.config(text="Stop Server")
                    self.host_status_label.config(text="Server: Running on %s:%d" % (ip, port))
                    self.log_host("Server started on %s:%d" % (ip, port))
                    
                    # Start server thread
                    server_thread = threading.Thread(target=self.accept_connections)
                    server_thread.setDaemon(True)
                    server_thread.start()
                    
                except socket.error as e:
                    messagebox.showerror("Error", "Failed to bind to address: " + str(e))
                    self.server_socket.close()
                    return
                    
            except Exception as e:
                messagebox.showerror("Error", str(e))
                self.stop_server()
                return
        else:
            self.stop_server()
    
    def stop_server(self):
        self.is_listening = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        self.start_btn.config(text="Start Server")
        self.host_status_label.config(text="Server: Stopped")
        self.log_host("Server stopped")
    
    def accept_connections(self):
        while self.is_listening:
            try:
                client, addr = self.server_socket.accept()
                handler = threading.Thread(target=self.handle_client, args=(client, addr))
                handler.setDaemon(True)
                handler.start()
            except:
                if self.is_listening:
                    self.log_host("Error accepting connection")
                break
    
    def handle_client(self, client, addr):
        try:
            # Receive filename length (8 bytes, padded ASCII number)
            name_length = int(client.recv(8).decode('ascii'))
            if not name_length:
                return
                
            # Receive filename
            filename = client.recv(name_length).decode('utf-8')
            if not filename:
                return
                
            # Receive file size (16 bytes, padded ASCII number)
            file_size = int(client.recv(16).decode('ascii'))
            if not file_size:
                return
                
            # Prepare file path
            filepath = os.path.join(self.received_dir, filename)
            
            # Receive file data
            received = 0
            with open(filepath, 'wb') as f:
                while received < file_size:
                    chunk = client.recv(min(32768, file_size - received))
                    if not chunk:
                        break
                    f.write(chunk)
                    received += len(chunk)
            
            self.log_host("Received file %s from %s" % (filename, addr[0]))
            
        except Exception as e:
            self.log_host("Error handling client %s: %s" % (addr[0], str(e)))
        finally:
            try:
                client.close()
            except:
                pass
    
    def watch_directory(self):
        while True:
            try:
                files = os.listdir(self.base_dir)
                for filename in files:
                    filepath = os.path.join(self.base_dir, filename)
                    if os.path.isfile(filepath) and not filename.startswith('.'):
                        if filename != os.path.basename(__file__):
                            try:
                                # Move to sent folder
                                new_path = os.path.join(self.sent_dir, filename)
                                shutil.move(filepath, new_path)
                                self.send_file(new_path)
                            except:
                                pass
            except:
                pass
            time.sleep(1)
    
    def send_file(self, filepath):
        try:
            filename = os.path.basename(filepath)
            filesize = os.path.getsize(filepath)
            
            # Create socket with timeout
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)
            
            try:
                # Connect to server
                sock.connect((self.server_ip.get(), int(self.server_port.get())))
                
                # Send filename length (8 bytes, padded ASCII number)
                name_bytes = filename.encode('utf-8')
                sock.send(str(len(name_bytes)).zfill(8).encode('ascii'))
                
                # Send filename
                sock.send(name_bytes)
                
                # Send file size (16 bytes, padded ASCII number)
                sock.send(str(filesize).zfill(16).encode('ascii'))
                
                # Send file data
                with open(filepath, 'rb') as f:
                    while True:
                        chunk = f.read(32768)  # 32KB chunks
                        if not chunk:
                            break
                        sock.send(chunk)
                
                self.log("File %s sent successfully" % filename)
                
            except socket.error as e:
                self.log("Connection failed: " + str(e))
            finally:
                sock.close()
                
        except Exception as e:
            self.log("Error sending file: " + str(e))
    
    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.insert(tk.END, "[%s] %s\n" % (timestamp, message))
        self.log_text.see(tk.END)
    
    def log_host(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.host_log_text.insert(tk.END, "[%s] %s\n" % (timestamp, message))
        self.host_log_text.see(tk.END)

if __name__ == "__main__":
    try:
        app = FileTransferGUI()
        # Start directory watcher thread
        watcher = threading.Thread(target=app.watch_directory)
        watcher.setDaemon(True)
        watcher.start()
        # Start GUI
        app.mainloop()
    except Exception as e:
        messagebox.showerror("Error", str(e))