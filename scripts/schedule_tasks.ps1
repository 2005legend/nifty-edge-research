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
$deskPython = Join-Path $project '.venv-desk\Scripts\python.exe'  # TradingAgents' own environment (SP4)
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
    # record and live also start at logon and retry at 09:05 and 09:30: on 23 Oct 2026 Windows restarted at 08:54
    # and the recorder never ran. A second copy exits at once (run lock), so the extra starts are harmless.
    @{ Name = 'record';         At = '08:55'; Args = 'record';           Hours = 8; Wake = $true; Retry = @('09:05', '09:30'); Logon = $true },
    @{ Name = 'macro-intraday'; At = '08:58'; Args = 'macro --intraday'; Hours = 8 },
    # SP3: alerts, paper trades and the dashboard (http://127.0.0.1:8000) until 15:35.
    @{ Name = 'live';           At = '09:10'; Args = 'live';             Hours = 7; Wake = $true; Retry = @('09:20', '09:40'); Logon = $true },
    @{ Name = 'eod';            At = '18:35'; Args = 'eod';              Hours = 6; Wake = $true },
    @{ Name = 'macro-evening';  At = '18:35'; Args = 'macro';            Hours = 1 },
    # Retries errored history chunks and adds recent days; skips everything already saved.
    @{ Name = 'backfill-history'; At = '20:30'; Args = 'backfill --what history'; Hours = 10 },
    # Rebuilds the derived tables from the day's downloads; the 09:10 live job refuses to start on stale tables.
    @{ Name = 'derive';         At = '23:30'; Args = 'derive';           Hours = 5 },
    # SP4 Path B (the pilot chose it on 22 Oct 2026): the compact AI desk brief to Telegram before the open.
    @{ Name = 'desk';           At = '08:30'; Args = 'desk';             Hours = 1 }
)

$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

foreach ($job in $jobs) {
    $exe = if ($job.Exe) { $job.Exe } else { $python }
    if (-not (Test-Path $exe)) { Write-Output "skipped quantdesk-$($job.Name): $exe not found"; continue }
    $run = if ($job.Run) { $job.Run } else { "-m quantdesk $($job.Args)" }
    $log = Join-Path $logDir "$($job.Name).log"
    # Runs inside a hidden PowerShell: a start marker, then the job, with all output appended to the log.
    $command = '$env:PYTHONUNBUFFERED=''1''; & {{ ''=== '' + (Get-Date -Format s) + '' {1} ===''; & ''{0}'' {1} }} *>> ''{2}''' -f $exe, $run, $log
    $action = New-ScheduledTaskAction -Execute 'powershell.exe' -WorkingDirectory $project `
        -Argument ('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command "{0}"' -f $command)

    if ($job.Daily) {
        $triggers = @((New-ScheduledTaskTrigger -Daily -At $job.At), (New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"))
    } else {
        $triggers = @(New-ScheduledTaskTrigger -Weekly -DaysOfWeek $weekdays -At $job.At)
        foreach ($at in @($job.Retry | Where-Object { $_ })) { $triggers += New-ScheduledTaskTrigger -Weekly -DaysOfWeek $weekdays -At $at }
        if ($job.Logon) { $triggers += New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME" }
    }

    $limit = if ($job.Hours -eq 0) { [TimeSpan]::Zero } else { New-TimeSpan -Hours $job.Hours }
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
        -MultipleInstances IgnoreNew -ExecutionTimeLimit $limit
    if ($job.Wake) { $settings.WakeToRun = $true }

    Register-ScheduledTask -TaskName "quantdesk-$($job.Name)" -Action $action -Trigger $triggers -Settings $settings `
        -Principal $principal -Description "quantdesk: $run. Log: $log" -Force | Out-Null
    Write-Output ("registered quantdesk-{0,-15} {1}  {2}" -f $job.Name, $job.At, $(if ($job.Daily) { 'daily + at logon' } else { 'Mon-Fri' }))
}
