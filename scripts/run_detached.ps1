<#
Runs a long command as a one-off Windows Task Scheduler job, hidden and logged, so closing a terminal,
restarting an app or logging the session out cannot kill it (anything started inside an app's terminal dies
with that app).

    powershell -ExecutionPolicy Bypass -File scripts\run_detached.ps1 -Name backfill-history -Run "-m quantdesk backfill --what history"
    powershell -ExecutionPolicy Bypass -File scripts\run_detached.ps1 -Name desk-pilot -Exe .venv-desk\Scripts\python.exe -Run "desk\run_pilot.py"

Output is appended to logs\tasks\<Name>.log. The job is registered as quantdesk-oneoff-<Name> with no trigger;
running the same Name again replaces it. A job that is still running is not started twice.
#>
param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Run,
    [string]$Exe = '.venv\Scripts\python.exe',
    [int]$Hours = 24
)

$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$exePath = if ([System.IO.Path]::IsPathRooted($Exe)) { $Exe } else { Join-Path $project $Exe }
if (-not (Test-Path $exePath)) { throw "$exePath not found" }
$logDir = Join-Path $project 'logs\tasks'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir "$Name.log"
$task = "quantdesk-oneoff-$Name"

$existing = Get-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue
if ($existing -and $existing.State -eq 'Running') { Write-Output "$task is already running; log: $log"; return }

$command = '$env:PYTHONUNBUFFERED=''1''; & {{ ''=== '' + (Get-Date -Format s) + '' {1} ===''; & ''{0}'' {1} }} *>> ''{2}''' -f $exePath, $Run, $log
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -WorkingDirectory $project `
    -Argument ('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command "{0}"' -f $command)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours $Hours)
Register-ScheduledTask -TaskName $task -Action $action -Settings $settings -Principal $principal `
    -Description "quantdesk one-off: $Run. Log: $log" -Force | Out-Null
Start-ScheduledTask -TaskName $task
Write-Output "started $task; log: $log"
