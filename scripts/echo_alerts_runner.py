#!/usr/bin/env python3
"""
Echo Backend Alerts — Checks for errors in Firebase Cloud Functions.
Sends alert to AAA OS Telegram if error rate exceeds threshold.

Runs every 1-2 hours via cron.
"""
import json
import subprocess
import urllib.request
from datetime import datetime, timezone

BOT_TOKEN = '8628864855:AAFWSgQCzUIGNtBK1dQk28rCJ7rqBo3v0zU'
CHAT_ID = '-5201056067'
PROJECT_ID = 'echo-79900'

# Thresholds
ERROR_THRESHOLD_1H = 50  # Alert if >50 errors in 1 hour
CRITICAL_FUNCTIONS = [
    'generateLyrics',
    'generateCustomMusic', 
    'generateSunoMusic',
    'processVoiceCloning',
    'ext-firestore-revenuecat-purchases-handler'
]


def run(cmd, input_text=None, timeout=300):
    # See daily_report_common.run: unbounded here means a hung gcloud call burns
    # the whole scheduler slot and _run_script drops the stderr (QUEUE #6).
    return subprocess.run(
        cmd, input=input_text, text=True, capture_output=True, check=False, timeout=timeout
    )


def send_telegram(text: str):
    payload = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": ""}).encode('utf-8')
    req = urllib.request.Request(
        f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
        data=payload,
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def get_cloud_function_errors(hours=1):
    """Query Cloud Logging for function errors in the last N hours."""
    # Calculate timestamp for N hours ago
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    cutoff_str = cutoff.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    cmd = [
        'gcloud', 'logging', 'read',
        f'resource.type="cloud_function" AND severity>=ERROR AND timestamp>="{cutoff_str}"',
        f'--project={PROJECT_ID}',
        '--limit=200',
        '--format=json'
    ]
    result = run(cmd)
    if result.returncode != 0:
        print(f"gcloud error: {result.stderr}")
        return []
    
    try:
        return json.loads(result.stdout or '[]')
    except json.JSONDecodeError:
        print(f"JSON parse error: {result.stdout[:200]}")
        return []


def categorize_errors(errors):
    """Group errors by function name and error type."""
    by_function = {}
    by_type = {}
    
    for err in errors:
        # Get function name
        func_name = err.get('resource', {}).get('labels', {}).get('function_name', 'unknown')
        by_function[func_name] = by_function.get(func_name, 0) + 1
        
        # Get error message snippet
        msg = err.get('jsonPayload', {}).get('message', '') or err.get('textPayload', '')
        if not msg:
            msg = str(err.get('jsonPayload', ''))
        
        # Categorize by error type
        if 'no user record' in msg.lower():
            err_type = 'UserNotFound (benign)'
        elif 'timeout' in msg.lower():
            err_type = 'Timeout'
        elif 'quota' in msg.lower() or 'rate limit' in msg.lower():
            err_type = 'QuotaExceeded'
        elif 'api' in msg.lower() and 'error' in msg.lower():
            err_type = 'APIError'
        elif 'authentication' in msg.lower() or 'unauthorized' in msg.lower():
            err_type = 'AuthError'
        else:
            err_type = 'Other'
        
        by_type[err_type] = by_type.get(err_type, 0) + 1
    
    return by_function, by_type


def main():
    print(f"Echo Backend Alerts — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    
    # Get errors from last hour
    errors = get_cloud_function_errors(hours=1)
    total_errors = len(errors)
    
    print(f"Total errors in last 1h: {total_errors}")
    
    if total_errors == 0:
        print("No errors detected. All clear.")
        return
    
    by_function, by_type = categorize_errors(errors)
    
    # Count non-benign errors (exclude UserNotFound which is common/expected)
    benign_count = by_type.get('UserNotFound (benign)', 0)
    actionable_errors = total_errors - benign_count
    
    print(f"By function: {json.dumps(by_function, indent=2)}")
    print(f"By type: {json.dumps(by_type, indent=2)}")
    print(f"Actionable errors (excluding benign): {actionable_errors}")
    
    # Check if we should alert
    should_alert = False
    alert_reasons = []
    
    # Alert if total actionable errors exceed threshold
    if actionable_errors >= ERROR_THRESHOLD_1H:
        should_alert = True
        alert_reasons.append(f"{actionable_errors} actionable errors (threshold: {ERROR_THRESHOLD_1H})")
    
    # Alert if any critical function has >10 errors
    for func in CRITICAL_FUNCTIONS:
        if by_function.get(func, 0) > 10:
            should_alert = True
            alert_reasons.append(f"{func}: {by_function[func]} errors")
    
    # Alert on specific severe error types
    if by_type.get('QuotaExceeded', 0) > 5:
        should_alert = True
        alert_reasons.append(f"QuotaExceeded: {by_type['QuotaExceeded']}")
    
    if by_type.get('AuthError', 0) > 5:
        should_alert = True
        alert_reasons.append(f"AuthError: {by_type['AuthError']}")
    
    if not should_alert:
        print(f"Errors below threshold. No alert needed.")
        print(f"  Benign (UserNotFound): {benign_count}")
        print(f"  Actionable: {actionable_errors}")
        return
    
    # Build alert message
    now_et = subprocess.run(['bash', '-lc', 'TZ="America/New_York" date +"%H:%M ET"'], 
                           capture_output=True, text=True).stdout.strip()
    
    func_breakdown = "\n".join([f"  • {k}: {v}" for k, v in sorted(by_function.items(), key=lambda x: -x[1])[:5]])
    type_breakdown = "\n".join([f"  • {k}: {v}" for k, v in sorted(by_type.items(), key=lambda x: -x[1])])
    
    alert = f"""🚨 Echo Backend Alert — {now_et}

⚠️ TRIGGER: {', '.join(alert_reasons)}

📊 ERRORS (last 1h): {total_errors}

By Function:
{func_breakdown}

By Type:
{type_breakdown}

Action: Check Firebase Console → Functions → Logs
https://console.firebase.google.com/project/echo-79900/functions/logs"""
    
    print(alert)
    res = send_telegram(alert)
    print('TELEGRAM_SENT_OK')
    print(json.dumps(res))


if __name__ == '__main__':
    main()
