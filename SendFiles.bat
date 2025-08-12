@echo off
echo ====================================================
echo Windows XP File Sender Launcher
echo ====================================================
echo.
echo This launcher will help you send files from this computer.
echo.
echo Please enter the IP address of the receiving computer:
set /p server_ip=IP Address: 

if "%server_ip%"=="" (
    echo Error: IP address is required.
    echo Press any key to exit...
    pause > nul
    exit /b
)

echo.
echo Starting file sender with target: %server_ip%
echo.
echo Place files in this folder to send them automatically.
echo Sent files will be moved to the "sent" folder.
echo.
echo Press Ctrl+C to stop the program.
echo.

file_transfer_xp.exe send %server_ip%