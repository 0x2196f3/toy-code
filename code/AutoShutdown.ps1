# AutoShutdown.ps1
# ---------------------
# Configuration & Installation Guide (README)
#
# Overview:
# This script runs at system startup (no logged-in user required) and checks overall CPU usage.
# If CPU is below 10% continuously for 1 hour, it initiates a shutdown.
#
# Installation (recommended: Scheduled Task):
#
# 1) Save this file to: C:\Scripts\AutoShutdown.ps1
#
# 2) Create the folder if needed:
#    - Open an elevated PowerShell prompt and run:
#      New-Item -Path "C:\Scripts" -ItemType Directory -Force
#
# 3) Create a Scheduled Task to run at system startup:
#    - Open Task Scheduler -> Create Task
#    - Name: AutoShutdownIfIdle
#    - Security options:
#      * Select "Run whether user is logged on or not"
#      * Check "Run with highest privileges"
#      * Configure for: your Windows version (e.g., Windows 10/11)
#    - Triggers:
#      * New -> Begin the task: At startup
#      * (Optional) Delay task for 30 seconds
#    - Actions:
#      * New -> Program/script: C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe
#      * Add arguments:
#        -NoProfile -ExecutionPolicy Bypass -File "C:\Scripts\AutoShutdown.ps1"
#    - Conditions:
#      * Uncheck "Start the task only if the computer is on AC power" if you want to allow shutdown on battery
#    - Settings:
#      * Allow task to be run on demand
#      * If the task is already running, choose "Do not start a new instance"
#    - Save. Provide admin credentials when prompted.
#
# 4) Optional: create a small .bat to run the script manually:
#    C:\Scripts\AutoShutdownStartup.bat:
#    ---------------------------------
#    @echo off
#    powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Scripts\AutoShutdownIfIdle.ps1"
#
# 5) Testing:
#    - Run the script manually in an elevated PowerShell to verify behavior before enabling the scheduled task:
#      powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Scripts\AutoShutdownIfIdle.ps1"
#
# 6) Notes & cautions:
#    - This measures total CPU usage only; services or periodic tasks will reset the idle timer.
#    - The script issues: shutdown.exe /s /t 60 with a 60s warning. Change /t 0 for immediate shutdown.
#    - Ensure ExecutionPolicy and task credentials allow the script to run at startup.
#    - To log CPU readings or exclude certain processes, modify the script below.
#
# End of README


# Checks CPU avg over samples; if <10% continuously for 1 hour, shuts down.
$sampleIntervalSeconds = 10
$samplesNeeded = [int](3600 / $sampleIntervalSeconds)  # 1 hour window
$threshold = 10.0

# Function: get total CPU % (averaged over a short internal sample)
function Get-TotalCpu {
    $c1 = Get-Counter '\Processor(_Total)\% Processor Time'
    return [math]::Round($c1.CounterSamples.CookedValue,2)
}

# Main loop
$consecutiveLow = 0
while ($true) {
    try {
        $cpu = Get-TotalCpu
    } catch {
        Start-Sleep -Seconds $sampleIntervalSeconds
        continue
    }

    if ($cpu -lt $threshold) {
        $consecutiveLow++
    } else {
        $consecutiveLow = 0
    }

    if ($consecutiveLow -ge $samplesNeeded) {
        # Optionally log timestamp
        Start-Process -FilePath "shutdown.exe" -ArgumentList "/s /t 60 /c `"`Automatic shutdown: CPU <$threshold% for 1 hour`"" -WindowStyle Hidden
        exit 0
    }

    Start-Sleep -Seconds $sampleIntervalSeconds
}
