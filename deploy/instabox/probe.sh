#!/usr/bin/env bash
# InstaBox pilot probe: can this machine do quantdesk's job? Uses no credentials and changes nothing.
#
#   bash deploy/instabox/probe.sh            # checks, then starts the heartbeat in the background
#   python3 deploy/instabox/heartbeat.py --report   # the next day: did the machine pause?
#
# Reports: machine size, where it runs (outbound IP and country), and whether NSE, BSE, Angel One, Telegram and
# Groq answer from here. NSE often refuses cloud addresses (HTTP 403); that would break the evening downloads.

day=$(date -d "yesterday" +%Y%m%d 2>/dev/null || date +%Y%m%d)
ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

code() { curl -s -o /dev/null -m 20 -A "$ua" -w "%{http_code}" "$1"; }

echo "== machine"
python3 --version
echo "cpus: $(nproc)  memory: $(free -h | awk '/Mem:/ {print $2}')  disk free: $(df -h /data 2>/dev/null | awk 'NR==2 {print $4}')"
echo "timezone: $(date +%Z) $(date)"

echo "== where it runs"
curl -s -m 20 https://ipinfo.io/json | grep -E '"(ip|city|region|country|org)"'

echo "== can it reach the services (200/401/403 = reachable; 000 = blocked or down)"
echo "NSE home:                $(code https://www.nseindia.com)"
echo "NSE F&O bhavcopy $day:   $(code "https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_${day}_F_0000.csv.zip")"
echo "NSE Nifty 50 list:       $(code https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv)"
echo "BSE F&O bhavcopy $day:   $(code "https://www.bseindia.com/download/Bhavcopy/Derivative/BhavCopy_BSE_FO_0_0_0_${day}_F_0000.CSV")"
echo "Angel One API:           $(code https://apiconnect.angelone.in/)"
echo "Angel One master file:   $(code https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json)"
echo "Telegram API:            $(code https://api.telegram.org)"
echo "Groq API:                $(code https://api.groq.com/openai/v1/models)"

echo "== heartbeat"
here="$(cd "$(dirname "$0")" && pwd)"
if pgrep -f "heartbeat.py" > /dev/null; then
  echo "already running"
else
  nohup python3 "$here/heartbeat.py" > /dev/null 2>&1 &
  echo "started: a timestamp every minute in $here/heartbeat.log, and 'ok' on port 8080"
fi
echo "Next: expose port 8080 as a public URL, then disconnect. Tomorrow: python3 $here/heartbeat.py --report"
