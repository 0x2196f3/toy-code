@echo off
setlocal

:: Set the NetConnectionID of the network adapter
set "adapterID=Ethernet 2"

:: Get the current status of the network adapter
for /f "tokens=2 delims==" %%i in ('wmic nic where "NetConnectionID='%adapterID%'" get NetEnabled /value ^| find "="') do set "status=%%i"

:: Check if the adapter is enabled or disabled
if "%status%"=="TRUE" (
    echo Disabling the adapter...
    wmic path win32_networkadapter where "NetConnectionID='%adapterID%'" call Disable
) else (
    echo Enabling the adapter...
    wmic path win32_networkadapter where "NetConnectionID='%adapterID%'" call Enable
)

endlocal
