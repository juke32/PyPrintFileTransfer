@echo off
setlocal
pushd "%~dp0"

rem Prefer .pyw to avoid console; fallback to .py
set "SCRIPT="
for /f "delims=" %%S in ('dir /b /a:-d "*file_transfer_xp.pyw"') do (
  set "SCRIPT=%%~fS"
  goto :found
)
for /f "delims=" %%S in ('dir /b /a:-d "*file_transfer_xp.py"') do (
  set "SCRIPT=%%~fS"
  goto :found
)

echo Script not found: *file_transfer_xp.py[w]
popd
endlocal
goto :eof

:found
rem Launch using file association (uses pythonw.exe for .pyw)
start "" "%SCRIPT%" receive

popd
endlocal
