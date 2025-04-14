import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import socket
import threading
import os
import shutil
from datetime import datetime
import sys
import time

# Try to import Windows-specific modules
try:
    import win32gui
    import win32con
    import win32api
    import win32gui_struct
    HAS_SYSTEM_TRAY = True
except ImportError:
    HAS_SYSTEM_TRAY = False

class FileTransferGUI(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title("File Transfer Application")
        self.geometry("800x600")
        
        # Set application icon for both window and taskbar
        self.icon_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "icon0.1.ico")
        if os.path.exists(self.icon_path):
            try:
                # Set window icon - use older Windows API method for XP compatibility
                hwnd = win32gui.GetParent(self.winfo_id())
                large_icon = win32gui.LoadImage(
                    0, self.icon_path, win32con.IMAGE_ICON,
                    win32api.GetSystemMetrics(win32con.SM_CXICON),
                    win32api.GetSystemMetrics(win32con.SM_CYICON),
                    win32con.LR_LOADFROMFILE
                )
                small_icon = win32gui.LoadImage(
                    0, self.icon_path, win32con.IMAGE_ICON,
                    win32api.GetSystemMetrics(win32con.SM_CXSMICON),
                    win32api.GetSystemMetrics(win32con.SM_CYSMICON),
                    win32con.LR_LOADFROMFILE
                )
                win32gui.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_BIG, large_icon)
                win32gui.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_SMALL, small_icon)
            except:
                # Fallback to tkinter method if Windows API fails
                try:
                    self.iconbitmap(default=self.icon_path)
                    self.iconbitmap(self.icon_path)
                except:
                    pass
        
        # Initialize system tray variables
        self.is_minimized = False
        self.hwnd = None
        self.notify_id = None
        self.has_tray = HAS_SYSTEM_TRAY
        
        # Initialize base directory
        self.base_dir = self.get_application_path()
        self.sent_dir = os.path.join(self.base_dir, "sent")
        self.received_dir = os.path.join(self.base_dir, "received")
        
        # Initialize print_filetypes with default values
        self.print_filetypes = {'.pdf', '.png'}
        
        # Create directories
        for directory in [self.sent_dir, self.received_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
        
        # Network variables
        self.server_socket = None
        self.is_listening = False
        self.is_client_running = False
        self.watcher_thread = None
        
        # GUI setup
        self.create_gui()
        
        # Set up system tray if available
        if self.has_tray:
            try:
                self.setup_tray()
            except:
                self.has_tray = False
        
        # Bind only window close event, not minimize
        self.protocol('WM_DELETE_WINDOW', self.on_closing)

    def setup_tray(self):
        """Set up system tray icon and functionality"""
        try:
            # Register window class
            wc = win32gui.WNDCLASS()
            hinst = wc.hInstance = win32api.GetModuleHandle(None)
            wc.lpszClassName = "FileTransferTray"
            wc.lpfnWndProc = {
                win32con.WM_DESTROY: self.on_destroy,
                win32con.WM_COMMAND: self.on_command,
                win32con.WM_USER + 20: self.on_tray_notification,
            }

            # Register the window class
            self.classAtom = win32gui.RegisterClass(wc)
            
            # Create the window
            style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
            self.hwnd = win32gui.CreateWindow(
                self.classAtom, "FileTransferTray", style,
                0, 0, win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT,
                0, 0, hinst, None
            )

            # Load icon for system tray
            if os.path.exists(self.icon_path):
                try:
                    hicon = win32gui.LoadImage(
                        None, 
                        self.icon_path,
                        win32con.IMAGE_ICON,
                        0, 0,  # Use actual size
                        win32con.LR_LOADFROMFILE
                    )
                except:
                    hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)
            else:
                hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)

            # Create the system tray icon with tooltip
            flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP | win32gui.NIF_INFO
            nid = (
                self.hwnd,
                0,
                flags,
                win32con.WM_USER + 20,
                hicon,
                "File Transfer Application"
            )
            
            # Add icon to system tray
            win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
            self.notify_id = nid
            
        except Exception as e:
            print("Failed to set up system tray:", str(e))
            self.has_tray = False

    def on_tray_notification(self, hwnd, msg, wparam, lparam):
        """Handle tray icon events"""
        if lparam == win32con.WM_LBUTTONDBLCLK:  # Double click
            self.show_window()
        elif lparam == win32con.WM_RBUTTONUP:  # Right click
            self.show_menu()
        return True

    def show_menu(self):
        """Show the tray icon context menu"""
        menu = win32gui.CreatePopupMenu()
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1, "Show")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 2, "Exit")

        pos = win32gui.GetCursorPos()
        win32gui.SetForegroundWindow(self.hwnd)
        win32gui.TrackPopupMenu(
            menu,
            win32con.TPM_LEFTALIGN,
            pos[0],
            pos[1],
            0,
            self.hwnd,
            None
        )
        win32gui.PostMessage(self.hwnd, win32con.WM_NULL, 0, 0)

    def on_command(self, hwnd, msg, wparam, lparam):
        """Handle menu commands"""
        id = win32api.LOWORD(wparam)
        if id == 1:  # Show
            self.show_window()
        elif id == 2:  # Exit
            self.quit_application()
        return True

    def show_window(self):
        """Show the main window"""
        self.is_minimized = False
        self.deiconify()
        self.state('normal')
        self.focus_force()

    def on_closing(self):
        """Handle window closing"""
        if self.has_tray:
            self.withdraw()
            self.is_minimized = True
            # Refresh system tray icon when minimizing
            if self.notify_id:
                try:
                    win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, self.notify_id)
                except:
                    pass
        else:
            if messagebox.askokcancel("Quit", "Do you want to quit the application?"):
                self.quit_application()

    def quit_application(self):
        """Clean up and exit the application"""
        try:
            if self.has_tray and self.notify_id:
                win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, self.notify_id)
            if self.is_listening:
                self.stop_server()
            if self.is_client_running:
                self.is_client_running = False
            self.destroy()
        except:
            self.destroy()

    def on_destroy(self, hwnd, msg, wparam, lparam):
        """Handle window destruction"""
        self.quit_application()
        return True

    def get_application_path(self):
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))

    def test_network_status(self):
        """Test network connectivity at startup"""
        try:
            # Create a test socket to verify network stack
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(2)
            
            # Log local network information
            self.log("Network Diagnostic Information:")
            self.log("Hostname: " + socket.gethostname())
            
            # Get and log all network interfaces
            for ip in self.get_local_ips():
                self.log("Local IP: " + ip)
            
            # Try to resolve a known host
            try:
                google_ip = socket.gethostbyname("www.google.com")
                self.log("Internet connectivity: OK (resolved www.google.com to " + google_ip + ")")
            except Exception as e:
                self.log("Warning: Cannot resolve external addresses: " + str(e))
            
            test_socket.close()
            
        except Exception as e:
            error_msg = "Network test failed. This might affect file transfers.\nError: " + str(e)
            self.log("ERROR: " + error_msg)
            messagebox.showwarning("Network Warning", error_msg)

    def get_local_ips(self):
        """Get all available network interfaces"""
        try:
            hostname = socket.gethostname()
            ips = set()
            
            # Get all network interfaces
            try:
                # Try getting all addresses including IPv4 and IPv6
                addrinfo = socket.getaddrinfo(hostname, None)
                for addr in addrinfo:
                    ip = addr[4][0]
                    if not ip.startswith('127.') and ':' not in ip:  # Exclude localhost and IPv6
                        ips.add(ip)
            except:
                pass
            
            # Fallback method
            try:
                ip = socket.gethostbyname(hostname)
                if not ip.startswith('127.'):
                    ips.add(ip)
            except:
                pass
            
            # Add fallback IP if no other IPs found
            if not ips:
                ips.add('127.0.0.1')
            
            return sorted(list(ips))
        except:
            return ['127.0.0.1']

    def get_system_printers(self):
        """Get list of available printers"""
        printers = ['No Printer', 'Default Printer']
        try:
            # Try using Windows API directly
            import win32print
            for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL, None, 1):
                printers.append(printer[2])
        except:
            try:
                # Fallback to checking common printer locations
                if os.name == 'nt':  # Windows
                    import winreg
                    printer_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                        "SYSTEM\\CurrentControlSet\\Control\\Print\\Printers")
                    try:
                        i = 0
                        while True:
                            printer_name = winreg.EnumKey(printer_key, i)
                            if printer_name not in printers:
                                printers.append(printer_name)
                            i += 1
                    except WindowsError:
                        pass
            except:
                pass
        return printers

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
        
        # Add start button
        self.client_start_btn = ttk.Button(net_frame, text="Start Client", command=self.toggle_client)
        self.client_start_btn.grid(row=0, column=4, padx=5, pady=5)
        
        # Status
        status_frame = ttk.LabelFrame(self.client_frame, text="Status")
        status_frame.pack(fill="x", padx=5, pady=5)
        self.status_label = ttk.Label(status_frame, text="Stopped")
        self.status_label.pack(padx=5, pady=5)
        
        # Log
        log_frame = ttk.LabelFrame(self.client_frame, text="Activity Log")
        log_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15)
        self.log_text.pack(fill="both", expand=True)
    
    def setup_host_tab(self):
        # Network Settings Frame
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
        
        # Auto Print Frame
        print_frame = ttk.LabelFrame(self.host_frame, text="Optional Auto Print")
        print_frame.pack(fill="x", padx=5, pady=5)
        
        # Printer selection
        ttk.Label(print_frame, text="Printer:").grid(row=0, column=0, padx=5, pady=5)
        self.printer_var = tk.StringVar(value="No Printer")
        self.printer_combo = ttk.Combobox(print_frame, textvariable=self.printer_var)
        self.printer_combo['values'] = self.get_system_printers()
        self.printer_combo.grid(row=0, column=1, padx=5, pady=5)
        self.printer_combo.current(0)
        
        # Refresh printer list button
        ttk.Button(print_frame, text="⟳", width=3, command=self.refresh_printers).grid(row=0, column=2, padx=2, pady=5)
        
        # File types
        ttk.Label(print_frame, text="File Types:").grid(row=0, column=3, padx=5, pady=5)
        self.filetype_var = tk.StringVar(value="pdf, png")
        self.filetype_entry = ttk.Entry(print_frame, textvariable=self.filetype_var, width=30)
        self.filetype_entry.grid(row=0, column=4, padx=5, pady=5)
        self.filetype_entry.bind('<FocusOut>', self.update_filetypes)
        
        # Status Frame
        status_frame = ttk.LabelFrame(self.host_frame, text="Server Status")
        status_frame.pack(fill="x", padx=5, pady=5)
        self.host_status_label = ttk.Label(status_frame, text="Server: Stopped")
        self.host_status_label.pack(padx=5, pady=5)
        
        # Log Frame
        log_frame = ttk.LabelFrame(self.host_frame, text="Server Log")
        log_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.host_log_text = scrolledtext.ScrolledText(log_frame, height=15)
        self.host_log_text.pack(fill="both", expand=True)
    
    def refresh_printers(self):
        current = self.printer_var.get()
        new_values = self.get_system_printers()
        self.printer_combo['values'] = new_values
        if current in new_values:
            self.printer_var.set(current)
        else:
            self.printer_var.set('No Printer')
        self.log_host("Printer list refreshed")

    def update_filetypes(self, event=None):
        filetypes = self.filetype_var.get().lower()
        # Convert string to set of extensions
        new_types = set()
        for ft in filetypes.split(','):
            ft = ft.strip()
            if ft:
                if not ft.startswith('.'):
                    ft = '.' + ft
                new_types.add(ft)
        self.print_filetypes = new_types
        # Update display with normalized format
        self.filetype_var.set(', '.join(sorted(t[1:] for t in self.print_filetypes)))

    def toggle_server(self):
        if not self.is_listening:
            try:
                ip = self.listen_ip.get()
                port = int(self.listen_port.get())
                
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                
                try:
                    # Log binding attempt
                    self.log_host(f"Attempting to bind to {ip}:{port}")
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
                    error_msg = f"Failed to bind to address {ip}:{port}: {str(e)}"
                    self.log_host("ERROR: " + error_msg)
                    messagebox.showerror("Error", error_msg)
                    self.server_socket.close()
                    return
                    
            except Exception as e:
                self.log_host("ERROR: Server start failed: " + str(e))
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
            self.log_host(f"New connection from {addr[0]}:{addr[1]}")
            
            # Set socket timeout
            client.settimeout(30)
            self.log_host(f"Waiting for filename length from {addr[0]}")
            
            name_length_data = client.recv(8)
            self.log_host(f"Received raw filename length data: {name_length_data!r}")
            
            if not name_length_data:
                self.log_host(f"Client {addr[0]} disconnected - no filename length received (received empty data)")
                return
                
            try:
                name_length = int(name_length_data.decode('ascii'))
                self.log_host(f"Decoded filename length: {name_length}")
            except ValueError as e:
                self.log_host(f"Error decoding filename length from {addr[0]}: {str(e)}, raw data: {name_length_data!r}")
                return
                
            filename_data = client.recv(name_length)
            self.log_host(f"Received raw filename data: {filename_data!r}")
            
            if not filename_data:
                self.log_host(f"Client {addr[0]} disconnected - no filename received (received empty data)")
                return
                
            try:
                filename = filename_data.decode('utf-8')
                self.log_host(f"Decoded filename: {filename}")
            except UnicodeDecodeError as e:
                self.log_host(f"Error decoding filename from {addr[0]}: {str(e)}, raw data: {filename_data!r}")
                return
                
            size_data = client.recv(16)
            self.log_host(f"Received raw file size data: {size_data!r}")
            
            if not size_data:
                self.log_host(f"Client {addr[0]} disconnected - no file size received (received empty data)")
                return
                
            try:
                file_size = int(size_data.decode('ascii'))
                self.log_host(f"Decoded file size: {file_size}")
            except ValueError as e:
                self.log_host(f"Error decoding file size from {addr[0]}: {str(e)}, raw data: {size_data!r}")
                return
            
            self.log_host(f"Receiving file {filename} ({file_size} bytes) from {addr[0]}")
            
            filepath = os.path.join(self.received_dir, filename)
            if os.path.exists(filepath):
                self.log_host("File %s already exists - will overwrite" % filename)
            
            received = 0
            with open(filepath, 'wb') as f:
                while received < file_size:
                    chunk = client.recv(min(32768, file_size - received))
                    if not chunk:
                        self.log_host(f"Connection lost while receiving file - got {received}/{file_size} bytes")
                        break
                    f.write(chunk)
                    received += len(chunk)
                    if received % 327680 == 0:  # Log every 320KB
                        self.log_host(f"Received {received}/{file_size} bytes")
            
            if received == file_size:
                self.log_host(f"Successfully received file {filename} from {addr[0]}")
            else:
                self.log_host(f"WARNING: Incomplete file received from {addr[0]} - got {received}/{file_size} bytes")
            
            if self.printer_var.get() != "No Printer":
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext in self.print_filetypes:
                    self.print_file(filepath)
            
        except Exception as e:
            self.log_host(f"Error handling client {addr[0]}: {str(e)}")
        finally:
            try:
                client.close()
            except:
                pass

    def print_file(self, filepath):
        try:
            printer_name = self.printer_var.get()
            if printer_name and printer_name != "No Printer":
                os.startfile(filepath, "print")
                self.log_host("Sent %s to default printer" % os.path.basename(filepath))
        except Exception as e:
            self.log_host("Error printing file: %s" % str(e))

    def watch_directory(self):
        """Monitor directory for new files"""
        while self.is_client_running:
            try:
                # Only watch the base directory where the exe/script is located
                files = [f for f in os.listdir(self.base_dir) 
                        if os.path.isfile(os.path.join(self.base_dir, f))]
                
                for filename in files:
                    filepath = os.path.join(self.base_dir, filename)
                    
                    # Skip the executable itself and system files
                    if (not filename.startswith('.') and
                        not filename.endswith('.exe') and
                        not filename.endswith('.pyc') and
                        not filename.endswith('.pyd') and
                        not filename.endswith('.dll') and
                        filename != os.path.basename(sys.executable) and
                        filename != os.path.basename(__file__)):
                        
                        try:
                            # Move to sent folder (will overwrite if exists)
                            new_path = os.path.join(self.sent_dir, filename)
                            if os.path.exists(new_path):
                                self.log(f"File {filename} already exists in sent folder - will overwrite")
                            shutil.move(filepath, new_path)
                            self.send_file(new_path)
                        except Exception as e:
                            self.log(f"Error processing file {filename}: {str(e)}")
            except Exception as e:
                self.log(f"Directory watch error: {str(e)}")
            time.sleep(1)

    def send_file(self, filepath):
        try:
            filename = os.path.basename(filepath)
            filesize = os.path.getsize(filepath)
            
            server_ip = self.server_ip.get()
            server_port = int(self.server_port.get())
            
            # Log connection attempt
            self.log(f"Attempting to connect to {server_ip}:{server_port}")
            
            # Create socket with timeout
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)
            
            try:
                # Connect to server
                sock.connect((server_ip, server_port))
                self.log(f"Successfully connected to {server_ip}:{server_port}")
                
                # Send filename length (8 bytes, padded ASCII number)
                name_bytes = filename.encode('utf-8')
                name_length = str(len(name_bytes)).zfill(8).encode('ascii')
                self.log(f"Sending filename length: {name_length!r}")
                sock.send(name_length)
                
                # Send filename
                self.log(f"Sending filename: {name_bytes!r}")
                sock.send(name_bytes)
                
                # Send file size (16 bytes, padded ASCII number)
                size_bytes = str(filesize).zfill(16).encode('ascii')
                self.log(f"Sending file size: {size_bytes!r}")
                sock.send(size_bytes)
                
                # Send file data
                with open(filepath, 'rb') as f:
                    total_sent = 0
                    while True:
                        chunk = f.read(32768)  # 32KB chunks
                        if not chunk:
                            break
                        bytes_sent = sock.send(chunk)
                        total_sent += bytes_sent
                        self.log(f"Sent {total_sent}/{filesize} bytes")
                
                self.log("File %s sent successfully" % filename)
                
            except socket.error as e:
                error_msg = f"Connection to {server_ip}:{server_port} failed: {str(e)}"
                self.log("ERROR: " + error_msg)
                messagebox.showerror("Connection Error", error_msg)
            finally:
                sock.close()
                
        except Exception as e:
            self.log("ERROR: Failed to send file: %s" % str(e))
    
    def toggle_client(self):
        if not self.is_client_running:
            try:
                # Validate connection settings
                if not self.server_ip.get().strip():
                    messagebox.showerror("Error", "Please enter a server IP address")
                    return
                    
                try:
                    port = int(self.server_port.get())
                    if port < 1 or port > 65535:
                        raise ValueError("Invalid port number")
                except ValueError:
                    messagebox.showerror("Error", "Please enter a valid port number (1-65535)")
                    return
                
                # Start the watcher thread
                self.is_client_running = True
                self.watcher_thread = threading.Thread(target=self.watch_directory)
                self.watcher_thread.setDaemon(True)
                self.watcher_thread.start()
                
                # Update UI
                self.client_start_btn.config(text="Stop Client")
                self.status_label.config(text="Running - Watching for new files")
                self.log("Client started - watching for new files")
                
            except Exception as e:
                self.log("Error starting client: %s" % str(e))
                self.is_client_running = False
                return
        else:
            # Stop the client
            self.is_client_running = False
            self.client_start_btn.config(text="Start Client")
            self.status_label.config(text="Stopped")
            self.log("Client stopped")
    
    def log(self, message):
        # Replace f-strings with older % formatting for XP compatibility
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
        app.mainloop()
    except Exception as e:
        messagebox.showerror("Error", str(e))