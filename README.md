# File Transfer Application

A simple yet powerful application to transfer files between computers on your local network, with optional auto-print functionality.

## Features

- Easy file transfer between computers on the same network
- System tray integration for background operation
- Optional auto-printing of received files (turns into a print server)
- Activity logs for both sending and receiving
- Support for customizable print file types
- Simple and intuitive graphical interface

## How to Use

### Setup
1. ***Place the application in its own folder***
2. Run the application on both computers (sender and receiver)
4. Set the listening adapter on the host
5. Set the server ip the client will send to
6. Place any file in the same directory as the .exe
7. check the recieved folder in the host's .exe directory

### Host Computer (Receiving Files)
1. Go to the "Host" tab
2. Select your network interface from the "Listen IP" dropdown
3. Keep the default port (25565) or enter a custom port
4. Click "Start Server"
5. (Optional) Select a printer for auto-printing received files
6. (Optional) Set file types for auto-printing (default: pdf, png)

## System Requirements
- Windows operating system (trying to get windows xp to work)
- Both computers must be on the same virtual or local network

## Tips
- Double-click the system tray icon to show/hide the window
- Right-click the system tray icon for options
- Check the activity logs in both tabs for transfer status
- The application runs in the background when minimized
- Default port is 25565 (can be changed if needed)

## Folders
- `sent/`: Stores files after they've been sent
- `received/`: Stores incoming files from other computers

## Background
I have a virtual windows xp machine that used to be on bare metal / connected to an active directory server.
It cannot see printers for whatever reason and has some networking issues. This is my attempt to get around the file transfer issue.
I havent tested it on windowsxp but it worked on 3+ windows 11 machines so far, so I am hopefull.
If you don't see more than one release, assume that it works perfectly!
