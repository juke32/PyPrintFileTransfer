@echo off
rem ====================================================
rem Windows XP File Sender - Direct Python Script Version
rem ====================================================
echo.
echo Starting file sender with target: 100.0.0.126
echo Port: 25565
echo.
echo Place files in this folder to send them automatically.
echo Sent files will be moved to the "sent" folder.
echo.
echo Press Ctrl+C to stop the program.
echo.

rem Run the Python script directly instead of an executable
python file_transfer_xp.py send 100.0.0.126

echo.
echo File transfer process terminated.
echo Press any key to exit...
pause > nul