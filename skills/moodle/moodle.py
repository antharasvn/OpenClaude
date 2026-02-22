#!/usr/bin/env python3
"""
moodle.py — Fetch Moodle deadlines via Chrome CDP + Innopolis SSO.

Usage: python3 moodle.py [deadlines|courses]

Reads MOODLE_USERNAME and MOODLE_PASSWORD from environment.
Chrome must be running with --remote-debugging-port=9222.
"""
import asyncio
import json
import os
import sys
import time
import websockets
import urllib.request

CHROME_DEBUG = "http://localhost:9222"
CMD = sys.argv[1] if len(sys.argv) > 1 else "deadlines"


async def cdp(ws, method, params=None, cmd_id=1):
    msg = {"id": cmd_id, "method": method, "params": params or {}}
    await ws.send(json.dumps(msg))
    while True:
        resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=20))
        if resp.get("id") == cmd_id:
            return resp.get("result", {})


async def js(ws, expr, cmd_id=50):
    r = await cdp(ws, "Runtime.evaluate", {"expression": expr, "awaitPromise": True}, cmd_id=cmd_id)
    return r.get("result", {}).get("value")


async def navigate(ws, url, cmd_id=3, wait=4):
    await cdp(ws, "Page.navigate", {"url": url}, cmd_id=cmd_id)
    await asyncio.sleep(wait)


async def get_tab_ws():
    with urllib.request.urlopen(f"{CHROME_DEBUG}/json", timeout=5) as r:
        tabs = json.loads(r.read())
    tab = next((t for t in tabs if t["type"] == "page"), None)
    if not tab:
        with urllib.request.urlopen(f"{CHROME_DEBUG}/json/new", timeout=5) as r:
            tab = json.loads(r.read())
    return tab["webSocketDebuggerUrl"]


async def login(ws):
    """Authenticate via Innopolis SSO. Returns True if successful."""
    username = os.environ.get("MOODLE_USERNAME", "")
    password = os.environ.get("MOODLE_PASSWORD", "")
    if not username or not password:
        print("ERROR: MOODLE_USERNAME and MOODLE_PASSWORD must be set in .env", file=sys.stderr)
        sys.exit(1)

    # Check if already logged in
    await navigate(ws, "https://moodle.innopolis.university/my/", 3)
    current_url = await js(ws, "window.location.href", cmd_id=10)
    if current_url and "moodle.innopolis.university/my" in current_url:
        return True  # Already logged in

    # Go to login page and click SSO button
    await navigate(ws, "https://moodle.innopolis.university/login/index.php", 4, wait=4)
    sso_href = await js(ws, """
    (function() {
        for(var a of document.querySelectorAll('a')) {
            if(a.href && (a.href.includes('oauth2') || a.textContent.includes('Innopolis'))) {
                return a.href;
            }
        }
        return null;
    })()
    """, cmd_id=11)

    if not sso_href:
        print("ERROR: Could not find SSO login button on Moodle", file=sys.stderr)
        sys.exit(1)

    await navigate(ws, sso_href, 5, wait=5)

    # Fill credentials on SSO/ADFS page
    await js(ws, f"""
    (function() {{
        var u = document.querySelector('#userNameInput') ||
                document.querySelector('input[name="UserName"]') ||
                document.querySelector('input[type="email"]') ||
                document.querySelector('input[type="text"]');
        if(u) {{
            u.value = {json.dumps(username)};
            u.dispatchEvent(new Event('input', {{bubbles:true}}));
            u.dispatchEvent(new Event('change', {{bubbles:true}}));
        }}
        var p = document.querySelector('#passwordInput') ||
                document.querySelector('input[name="Password"]') ||
                document.querySelector('input[type="password"]');
        if(p) {{
            p.value = {json.dumps(password)};
            p.dispatchEvent(new Event('input', {{bubbles:true}}));
            p.dispatchEvent(new Event('change', {{bubbles:true}}));
        }}
        var btn = document.querySelector('#submitButton') ||
                  document.querySelector('input[type="submit"]') ||
                  document.querySelector('button[type="submit"]');
        if(btn) btn.click();
    }})()
    """, cmd_id=12)

    await asyncio.sleep(6)
    current_url = await js(ws, "window.location.href", cmd_id=13)
    if current_url and "moodle.innopolis.university" not in current_url:
        error = await js(ws, """
        document.querySelector('#errorMessage')?.textContent?.trim() ||
        document.querySelector('.error')?.textContent?.trim() || ''
        """, cmd_id=14)
        print(f"ERROR: Login failed. {error or 'Check credentials.'}", file=sys.stderr)
        sys.exit(1)

    return True


async def cmd_deadlines(ws):
    """Fetch and print upcoming deadlines."""
    await navigate(ws, "https://moodle.innopolis.university/calendar/view.php?view=upcoming", 40, wait=4)

    now_ts = int(time.time())
    future_ts = now_ts + 90 * 24 * 3600  # 90 days ahead

    sesskey = await js(ws, "M?.cfg?.sesskey || ''", cmd_id=41)

    result = await js(ws, f"""
    (async function() {{
        var sesskey = {json.dumps(sesskey or '')};
        var response = await fetch('/lib/ajax/service.php?sesskey=' + sesskey, {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify([{{
                index: 0,
                methodname: 'core_calendar_get_action_events_by_timesort',
                args: {{
                    timesortfrom: {now_ts},
                    timesortto: {future_ts},
                    limitnum: 50
                }}
            }}])
        }});
        var data = await response.json();
        if(data[0]?.data?.events) {{
            return JSON.stringify(data[0].data.events.map(e => ({{
                name: e.activityname || e.name,
                description: e.activitystr || '',
                course: e.course?.fullname || '',
                timestart: e.timestart,
                overdue: e.overdue || false,
                url: e.action?.url || e.url || ''
            }})));
        }}
        return JSON.stringify({{error: data}});
    }})()
    """, cmd_id=42)

    try:
        events = json.loads(result)
    except (json.JSONDecodeError, TypeError):
        print("Could not parse events response.")
        return

    if isinstance(events, dict) and "error" in events:
        print(f"API error: {events['error']}")
        return

    if not events:
        print("Нет предстоящих дедлайнов в ближайшие 90 дней.")
        return

    print(f"Предстоящие дедлайны (следующие 90 дней):\n")
    for e in events:
        dt = time.strftime("%d %b %Y, %H:%M", time.localtime(e["timestart"]))
        overdue = " ⚠️  ПРОСРОЧЕНО" if e["overdue"] else ""
        print(f"  {dt}{overdue}")
        print(f"  📝 {e['name']} — {e['description']}")
        print(f"  📚 {e['course']}")
        if e["url"]:
            print(f"  🔗 {e['url']}")
        print()


async def cmd_courses(ws):
    """List current semester (S26) courses."""
    await navigate(ws, "https://moodle.innopolis.university/my/courses.php", 50, wait=4)

    result = await js(ws, """
    (function() {
        var links = document.querySelectorAll('a[href*="course/view.php"]');
        var seen = new Set();
        var courses = [];
        links.forEach(l => {
            var text = l.textContent.trim();
            var href = l.href;
            if(text.includes('S26') && !seen.has(href)) {
                seen.add(href);
                courses.push({name: text, url: href});
            }
        });
        return JSON.stringify(courses);
    })()
    """, cmd_id=51)

    try:
        courses = json.loads(result)
    except (json.JSONDecodeError, TypeError):
        print("Could not parse courses.")
        return

    if not courses:
        print("Нет курсов S26 или не удалось загрузить список.")
        return

    print("Курсы текущего семестра [S26]:\n")
    for c in courses:
        print(f"  • {c['name']}")
        print(f"    {c['url']}")
        print()


async def main():
    ws_url = await get_tab_ws()
    async with websockets.connect(ws_url, max_size=10 * 1024 * 1024) as ws:
        await cdp(ws, "Page.enable", {}, cmd_id=1)
        await cdp(ws, "Runtime.enable", {}, cmd_id=2)

        await login(ws)

        if CMD == "courses":
            await cmd_courses(ws)
        else:
            await cmd_deadlines(ws)


if __name__ == "__main__":
    asyncio.run(main())
