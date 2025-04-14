# File Transfer Application

A simple yet powerful application to transfer files between windows computers on your local network, with optional auto-print functionality.

![image](https://github.com/user-attachments/assets/7841283b-059a-40d1-80d5-6954750bc97d)


## Features

- Easy file transfer between computers on the same network
- System tray integration for background operation
- Optional auto-printing of received files (basically a print server!)
- Activity logs for both sending and receiving
- Support for customizable print file types
- Simple and intuitive graphical interface

## How to Use

### Setup
1. ***Place the application in its own folder on each machine***
2. Run the application on both computers (sender and receiver)
4. On the Host: Set the listening adapter and click start
5. On the Client: Set the ip of the server and click start
6. Place any file in the same directory as the .exe on the client
7. check the recieved folder in the host's .exe directory

## System Requirements
- Windows operating system (trying to get windows xp to work)
- Both computers must be on the same virtual or local network

## Tips
- ***Right-click the system tray icon to close the application***
- Double-click the system tray icon to show/hide the window
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
