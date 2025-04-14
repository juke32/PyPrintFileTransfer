# File Transfer Application

A simple yet powerful application to transfer files between computers on your local network, with optional auto-print functionality.

## Features

- Easy file transfer between computers on the same network
- System tray integration for background operation
- Optional auto-printing of received files
- Activity logs for both sending and receiving
- Support for customizable print file types
- Simple and intuitive graphical interface

## How to Use

### Setup
1. Run the application on both computers (sender and receiver)
2. Make sure both computers are connected to the same network

### Host Computer (Receiving Files)
1. Go to the "Host" tab
2. Select your network interface from the "Listen IP" dropdown
3. Keep the default port (25565) or enter a custom port
4. Click "Start Server"
5. (Optional) Select a printer for auto-printing received files
6. (Optional) Set file types for auto-printing (default: pdf, png)

### Client Computer (Sending Files)
1. Go to the "Client" tab
2. Enter the Host computer's IP address
3. Enter the same port number as the Host
4. Click "Start Client"
5. Place files in the application folder to send them automatically
   - Files will be moved to the "sent" folder after transfer
   - Received files appear in the "received" folder

## System Requirements
- Windows operating system
- Network connectivity between computers
- Both computers must be on the same local network

## Tips
- Double-click the system tray icon to show/hide the window
- Right-click the system tray icon for options
- Check the activity logs in both tabs for transfer status
- The application runs in the background when minimized
- Default port is 25565 (can be changed if needed)

## Folders
- `sent/`: Stores files after they've been sent
- `received/`: Stores incoming files from other computers