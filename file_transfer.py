import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import socket
import threading
import os
import shutil
from datetime import datetime
import sys
import time
import json
from typing import Any, cast

# Try to import Windows-specific modules
try:
    import win32gui  # type: ignore
    import win32con  # type: ignore
    import win32api  # type: ignore
    import win32gui_struct  # type: ignore
    import win32print  # type: ignore
    HAS_SYSTEM_TRAY = True
except ImportError:
    # Ensure names exist to satisfy static analysis; will be unused at runtime when False
    from typing import Any, cast
    win32gui = cast(Any, None)
    win32con = cast(Any, None)
    win32api = cast(Any, None)
    win32gui_struct = cast(Any, None)
    win32print = cast(Any, None)
    HAS_SYSTEM_TRAY = False

# Registry helpers (autostart)
try:
    import winreg  # Python 3
except Exception:
    winreg = None

class FileTransferGUI(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title("File Transfer Application")
        self.geometry("800x600")
        
        # Set application icon for both window and taskbar
        self.icon_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "icon0.1.ico")
        if os.path.exists(self.icon_path):
            if HAS_SYSTEM_TRAY:
                try:
                    # Set window icon - use older Windows API method for XP compatibility
                    hwnd = win32gui.GetParent(self.winfo_id())  # type: ignore
                    large_icon = win32gui.LoadImage(  # type: ignore
                        0, self.icon_path, win32con.IMAGE_ICON,
                        win32api.GetSystemMetrics(win32con.SM_CXICON),
                        win32api.GetSystemMetrics(win32con.SM_CYICON),
                        win32con.LR_LOADFROMFILE
                    )
                    small_icon = win32gui.LoadImage(  # type: ignore
                        0, self.icon_path, win32con.IMAGE_ICON,
                        win32api.GetSystemMetrics(win32con.SM_CXSMICON),
                        win32api.GetSystemMetrics(win32con.SM_CYSMICON),
                        win32con.LR_LOADFROMFILE
                    )
                    win32gui.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_BIG, large_icon)  # type: ignore
                    win32gui.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_SMALL, small_icon)  # type: ignore
                except:
                    # Fallback to tkinter method if Windows API fails
                    try:
                        self.iconbitmap(default=self.icon_path)
                        self.iconbitmap(self.icon_path)
                    except:
                        pass
            else:
                try:
                    self.iconbitmap(default=self.icon_path)
                    self.iconbitmap(self.icon_path)
                except Exception:
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

        # Config and defaults
        self.config = {
            "listen_ip": "",
            "listen_port": 25565,
            "printer_name": "No Printer",
            "print_filetypes": [".pdf", ".png"],
            "start_server_on_launch": False,
            "start_minimized": False,
            "start_with_windows": False,
            # Client (optional)
            "server_ip": "",
            "server_port": 25565,
        }
        self.print_filetypes = set(self.config["print_filetypes"])
        self.config_path = self.get_config_path()
        self.load_config()  # populate self.config if present

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

        # Apply loaded config to UI and startup behavior
        self.apply_config_to_ui()

        # Start minimized if configured or flag provided
        if self.config.get("start_minimized") or "--minimized" in sys.argv:
            try:
                self.withdraw()
                self.is_minimized = True
            except Exception:
                pass

        # Optionally auto-start server on launch (config or CLI flag)
        if self.config.get("start_server_on_launch") or "--start-server" in sys.argv:
            try:
                # Avoid message boxes on auto start
                self.toggle_server()
            except Exception:
                pass

    def setup_tray(self):
        """Set up system tray icon and functionality"""
        try:
            # Register window class
            wc = win32gui.WNDCLASS()  # type: ignore
            hinst = wc.hInstance = win32api.GetModuleHandle(None)  # type: ignore
            wc.lpszClassName = "FileTransferTray"  # type: ignore
            wc.lpfnWndProc = {  # type: ignore
                win32con.WM_DESTROY: self.on_destroy,
                win32con.WM_COMMAND: self.on_command,
                win32con.WM_USER + 20: self.on_tray_notification,
            }

            # Register the window class
            self.classAtom = win32gui.RegisterClass(wc)  # type: ignore
            
            # Create the window
            style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
            self.hwnd = win32gui.CreateWindow(  # type: ignore
                self.classAtom, "FileTransferTray", style,
                0, 0, win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT,
                0, 0, hinst, None
            )

            # Load icon for system tray
            if os.path.exists(self.icon_path):
                try:
                    hicon = win32gui.LoadImage(  # type: ignore
                        0,
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
            win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)  # type: ignore
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
        menu = win32gui.CreatePopupMenu()  # type: ignore
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1, "Show")  # type: ignore
        win32gui.AppendMenu(menu, win32con.MF_STRING, 2, "Exit")  # type: ignore

        pos = win32gui.GetCursorPos()  # type: ignore
        win32gui.SetForegroundWindow(self.hwnd)  # type: ignore
        hwnd_int = cast(int, self.hwnd) if self.hwnd else 0
        rect: Any = None
        win32gui.TrackPopupMenu(  # type: ignore
            menu,
            win32con.TPM_LEFTALIGN,
            pos[0],
            pos[1],
            0,
            hwnd_int,
            rect
        )
        win32gui.PostMessage(self.hwnd, win32con.WM_NULL, 0, 0)  # type: ignore

    def on_command(self, hwnd, msg, wparam, lparam):
        """Handle menu commands"""
        id = win32api.LOWORD(wparam)  # type: ignore
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
                    win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, self.notify_id)  # type: ignore
                except:
                    pass
        else:
            if messagebox.askokcancel("Quit", "Do you want to quit the application?"):
                self.quit_application()

    def quit_application(self):
        """Clean up and exit the application"""
        try:
            # Save settings before exit
            try:
                self.save_config()
            except Exception:
                pass
            if self.has_tray and self.notify_id:
                win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, self.notify_id)  # type: ignore
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

    def get_config_path(self):
        """Store config next to the EXE/script for portability."""
        return os.path.join(self.base_dir, "pyprint-filetransfer-config.json")

    def load_config(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Merge known keys only
                for k in self.config:
                    if k in data:
                        self.config[k] = data[k]
                # Normalize
                if isinstance(self.config.get("print_filetypes"), list):
                    self.print_filetypes = set(ft.lower() if ft.startswith('.') else f".{ft.lower()}" for ft in self.config["print_filetypes"])  
        except Exception as e:
            # Non-fatal
            print("Failed to load config:", str(e))

    def save_config(self):
        try:
            # Sync from UI first
            try:
                self.config["listen_ip"] = self.listen_ip.get().strip()
            except Exception:
                pass
            try:
                self.config["listen_port"] = int(self.listen_port.get().strip())
            except Exception:
                pass
            try:
                self.config["printer_name"] = self.printer_var.get()
            except Exception:
                pass
            try:
                self.config["print_filetypes"] = sorted(list(self.print_filetypes))
            except Exception:
                pass
            try:
                self.config["server_ip"] = self.server_ip.get().strip()
            except Exception:
                pass
            try:
                self.config["server_port"] = int(self.server_port.get().strip())
            except Exception:
                pass

            # Settings toggles
            self.config["start_server_on_launch"] = bool(self.auto_start_server_var.get())
            self.config["start_minimized"] = bool(self.start_minimized_var.get())
            self.config["start_with_windows"] = bool(self.start_with_windows_var.get())

            # Persist
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)

            # Update Windows autostart if requested
            self.update_windows_autostart(self.config["start_with_windows"]) 

            self.log_host("Settings saved")
        except Exception as e:
            try:
                messagebox.showerror("Save Error", str(e))
            except Exception:
                print("Save Error:", str(e))

    def update_windows_autostart(self, enable):
        """Add/remove Run registry entry for current executable."""
        if not winreg:
            return
        try:
            # Only make sense for frozen EXE
            exe_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(sys.argv[0])
            app_name = "FileTransfer"
            run_key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_key_path, 0, winreg.KEY_ALL_ACCESS) as run_key:
                if enable:
                    # Add minimized flag so it doesn't pop up at boot
                    cmd = f'"{exe_path}" --minimized'
                    winreg.SetValueEx(run_key, app_name, 0, winreg.REG_SZ, cmd)
                else:
                    try:
                        winreg.DeleteValue(run_key, app_name)
                    except FileNotFoundError:
                        pass
        except Exception as e:
            self.log_host("Autostart update failed: %s" % str(e))

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
                    ip_str = str(ip)
                    if not ip_str.startswith('127.') and ':' not in ip_str:  # Exclude localhost and IPv6
                        ips.add(ip_str)
            except:
                pass
            
            # Fallback method
            try:
                ip = socket.gethostbyname(hostname)
                ip_str = str(ip)
                if not ip_str.startswith('127.'):
                    ips.add(ip_str)
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
            for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS, None, 1):
                pname = printer[2]
                if pname and pname not in printers:
                    printers.append(pname)
        except:
            try:
                # Fallback to checking common printer locations
                if os.name == 'nt' and winreg is not None:  # Windows and registry available
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
        self.settings_frame = ttk.Frame(self.notebook)

        # Add tabs
        self.notebook.add(self.client_frame, text='Client')
        self.notebook.add(self.host_frame, text='Host')
        self.notebook.add(self.settings_frame, text='Settings')

        # Build tab contents
        self.setup_client_tab()
        self.setup_host_tab()
        self.setup_settings_tab()
    
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

    def setup_settings_tab(self):
        """Settings that persist across restarts and control startup behavior."""
        cfg_frame = ttk.LabelFrame(self.settings_frame, text="Startup & Behavior")
        cfg_frame.pack(fill="x", padx=5, pady=5)

        self.auto_start_server_var = tk.BooleanVar(value=self.config.get("start_server_on_launch", False))
        self.start_minimized_var = tk.BooleanVar(value=self.config.get("start_minimized", False))
        self.start_with_windows_var = tk.BooleanVar(value=self.config.get("start_with_windows", False))

        ttk.Checkbutton(cfg_frame, text="Start server when application launches", variable=self.auto_start_server_var).grid(row=0, column=0, sticky='w', padx=5, pady=5, columnspan=2)
        ttk.Checkbutton(cfg_frame, text="Start minimized (to tray if available)", variable=self.start_minimized_var).grid(row=1, column=0, sticky='w', padx=5, pady=5, columnspan=2)
        ttk.Checkbutton(cfg_frame, text="Start with Windows (current user)", variable=self.start_with_windows_var).grid(row=2, column=0, sticky='w', padx=5, pady=5, columnspan=2)

        # Save button
        btn_row = ttk.Frame(cfg_frame)
        btn_row.grid(row=3, column=0, padx=5, pady=10, sticky='w')
        ttk.Button(btn_row, text="Save Settings", command=self.save_config).pack(side='left', padx=5)
        ttk.Button(btn_row, text="Reload Settings", command=self.apply_config_to_ui).pack(side='left', padx=5)

        # Info
        info = ttk.Label(self.settings_frame, text="Settings are saved to: %s" % self.config_path, wraplength=740, foreground="#555")
        info.pack(fill='x', padx=8, pady=4)

    def apply_config_to_ui(self):
        """Populate UI controls from loaded config."""
        try:
            # Host
            if self.config.get("listen_ip"):
                try:
                    self.listen_ip.set(self.config.get("listen_ip"))
                except Exception:
                    pass
            try:
                self.listen_port.delete(0, tk.END)
                self.listen_port.insert(0, str(self.config.get("listen_port", 25565)))
            except Exception:
                pass

            # Printers and file types
            try:
                printers = self.get_system_printers()
                self.printer_combo['values'] = printers
                pref = self.config.get("printer_name", "No Printer")
                if pref in printers:
                    self.printer_var.set(pref)
                else:
                    self.printer_var.set('No Printer')
            except Exception:
                pass

            self.print_filetypes = set(
                ft.lower() if ft.startswith('.') else f".{ft.lower()}"
                for ft in self.config.get("print_filetypes", [".pdf", ".png"]) 
            )
            # Update display with normalized format
            try:
                self.filetype_var.set(', '.join(sorted(t[1:] for t in self.print_filetypes)))
            except Exception:
                pass

            # Client
            try:
                self.server_ip.delete(0, tk.END)
                self.server_ip.insert(0, self.config.get("server_ip", ""))
                self.server_port.delete(0, tk.END)
                self.server_port.insert(0, str(self.config.get("server_port", 25565)))
            except Exception:
                pass

            # Settings toggles (if already created)
            if hasattr(self, 'auto_start_server_var'):
                self.auto_start_server_var.set(bool(self.config.get("start_server_on_launch", False)))
            if hasattr(self, 'start_minimized_var'):
                self.start_minimized_var.set(bool(self.config.get("start_minimized", False)))
            if hasattr(self, 'start_with_windows_var'):
                self.start_with_windows_var.set(bool(self.config.get("start_with_windows", False)))
        except Exception as e:
            print("apply_config_to_ui error:", str(e))
    
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
        # Persist change
        try:
            self.save_config()
        except Exception:
            pass

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
                sock = self.server_socket
                if not sock:
                    break
                client, addr = sock.accept()
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
            if not printer_name or printer_name == "No Printer":
                return

            # If Default Printer selected, just use shell default
            if printer_name == "Default Printer":
                try:
                    os.startfile(filepath, "print")
                    self.log_host("Sent %s to default printer" % os.path.basename(filepath))
                    return
                except Exception as e:
                    self.log_host("Default print failed, trying printto: %s" % str(e))

            # Try 'printto' verb to target a specific printer
            if win32api is not None:
                try:
                    # Surround printer name in quotes in case of spaces
                    win32api.ShellExecute(0, 'printto', filepath, '"%s"' % printer_name, '.', 0)
                    self.log_host("Sent %s to printer '%s'" % (os.path.basename(filepath), printer_name))
                    return
                except Exception as e:
                    self.log_host("printto failed: %s" % str(e))

            # Fallback: temporarily set default printer and use startfile
            if win32print is not None:
                try:
                    current = None
                    try:
                        current = win32print.GetDefaultPrinter()
                    except Exception:
                        current = None
                    try:
                        win32print.SetDefaultPrinter(printer_name)
                        os.startfile(filepath, "print")
                        self.log_host("Printed %s via temporary default '%s'" % (os.path.basename(filepath), printer_name))
                    finally:
                        try:
                            if current:
                                win32print.SetDefaultPrinter(current)
                        except Exception:
                            pass
                except Exception as e:
                    self.log_host("Temp default print failed: %s" % str(e))
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
                        filename != 'pyprint-filetransfer-config.json' and
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