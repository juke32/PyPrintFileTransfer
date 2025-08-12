@echo off
echo ====================================================
echo Windows XP File Receiver Launcher
echo ====================================================
echo.
echo This launcher will help you receive files on this computer.
echo.
echo Would you like to:
echo 1. Listen on all network interfaces (recommended)
echo 2. Listen on a specific IP address
echo.
set /p choice=Enter choice (1 or 2): 

if "%choice%"=="2" (
    echo.
    echo Please enter the IP address to listen on:
    set /p listen_ip=IP Address: 
    
    if "%listen_ip%"=="" (
        echo Error: IP address is required for this option.
        echo Press any key to exit...
        pause > nul
        exit /b
    )
    
    echo.
    echo Starting file receiver on IP: %listen_ip%
    echo.
    echo Received files will be saved to the "received" folder.
    echo.
    echo Press Ctrl+C to stop the program.
    echo.
    
    file_transfer_xp.exe receive %listen_ip%
) else (
    echo.
    echo Starting file receiver on all network interfaces.
    echo.
    echo Received files will be saved to the "received" folder.
    echo.
    echo Press Ctrl+C to stop the program.
    echo.
    
    file_transfer_xp.exe receive
)