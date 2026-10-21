<#
Registers the quantdesk daily jobs in Windows Task Scheduler for the current user.

    powershell -ExecutionPolicy Bypass -File scripts\schedule_tasks.ps1          # create or update the jobs
    powershell -ExecutionPolicy Bypass -File scripts\schedule_tasks.ps1 -Remove  # delete them

Jobs run hidden while you are logged in, so there is no window to close by accident. Each one appends its
output to logs\tasks\<job>.log. A job still running is never started a second time, a job missed while
the PC was off starts when it comes back on, and jobs keep running on battery.
#>
param([switch]$Remove)

$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$python = Join-Path $project '.venv\Scripts\python.exe'
$logDir = Join-Path $project 'logs\tasks'
$weekdays = 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'

if ($Remove) {
    Get-ScheduledTask -TaskName 'quantdesk-*' -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false
    Write-Output 'Removed all quantdesk-* tasks.'
    return
}

if (-not (Test-Path $python)) { throw "Python not found at $python. Create the .venv first (see docs\runbook.md)." }
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

# Times follow docs\runbook.md. Hours = 0 means no time limit (the news poller runs continuously).
$jobs = @(
    @{ Name = 'news';           At = '06:55'; Args = 'news';             Hours = 0; Daily = $true },
    @{ Name = 'macro-morning';  At = '07:30'; Args = 'macro';            Hours = 1 },
    @{ Name = 'record';         At = '08:55'; Args = 'record';           Hours = 8; Wake = $true },
    @{ Name = 'macro-intraday'; At = '08:58'; Args = 'macro --intraday'; Hours = 8 },
    @{ Name = 'eod';            At = '18:35'; Args = 'eod';              Hours = 6; Wake = $true },
    @{ Name = 'macro-evening';  At = '18:35'; Args = 'macro';            Hours = 1 }
)

$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

foreach ($job in $jobs) {
    $log = Join-Path $logDir "$($job.Name).log"
    # Runs inside a hidden PowerShell: a start marker, then the job, with all output appended to the log.
    $command = '$env:PYTHONUNBUFFERED=''1''; & {{ ''=== '' + (Get-Date -Format s) + '' {1} ===''; & ''{0}'' -m quantdesk {1} }} *>> ''{2}''' -f $python, $job.Args, $log
    $action = New-ScheduledTaskAction -Execute 'powershell.exe' -WorkingDirectory $project `
        -Argument ('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command "{0}"' -f $command)

    if ($job.Daily) {
        $triggers = @((New-ScheduledTaskTrigger -Daily -At $job.At), (New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"))
    } else {
        $triggers = @(New-ScheduledTaskTrigger -Weekly -DaysOfWeek $weekdays -At $job.At)
    }

    $limit = if ($job.Hours -eq 0) { [TimeSpan]::Zero } else { New-TimeSpan -Hours $job.Hours }
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
        -MultipleInstances IgnoreNew -ExecutionTimeLimit $limit
    if ($job.Wake) { $settings.WakeToRun = $true }

    Register-ScheduledTask -TaskName "quantdesk-$($job.Name)" -Action $action -Trigger $triggers -Settings $settings `
        -Principal $principal -Description "quantdesk: python -m quantdesk $($job.Args). Log: $log" -Force | Out-Null
    Write-Output ("registered quantdesk-{0,-15} {1}  {2}" -f $job.Name, $job.At, $(if ($job.Daily) { 'daily + at logon' } else { 'Mon-Fri' }))
}
