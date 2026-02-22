#!/usr/bin/env python3
"""
moodle.py — Moodle via Chrome CDP + Innopolis SSO.

Usage: python3 moodle.py <command> [args]

Commands:
  deadlines               — upcoming deadlines (next 90 days)
  courses                 — list current semester [S26] courses
  lectures [course_id]    — list lectures/resources for a course
  download <resource_id> [outdir]  — download a file resource

Reads MOODLE_USERNAME and MOODLE_PASSWORD from environment.
Chrome must be running with --remote-debugging-port=9222.
"""
import asyncio
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import websockets

CHROME_DEBUG = "http://localhost:9222"
CMD  = sys.argv[1] if len(sys.argv) > 1 else "deadlines"
ARGS = sys.argv[2:]

# Default NLP course ID
DEFAULT_COURSE_ID = 3440


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


async def cmd_lectures(ws):
    """List all resources (lectures, labs) for a course."""
    course_id = int(ARGS[0]) if ARGS else DEFAULT_COURSE_ID

    await navigate(ws, f"https://moodle.innopolis.university/course/view.php?id={course_id}", 60, wait=5)

    result = await js(ws, """
    (function() {
        var sections = [];
        var seen = new Set();
        document.querySelectorAll('li[id^="section-"]').forEach(function(sec) {
            var title = sec.querySelector('h3, .sectionname, .section-title')?.textContent?.trim() || '';
            var items = [];
            sec.querySelectorAll('a[href*="/mod/resource/"], a[href*="/mod/folder/"], a[href*="/mod/url/"]').forEach(function(a) {
                if(!seen.has(a.href)) {
                    seen.add(a.href);
                    var text = a.textContent.trim().replace(/\\s+/g, ' ');
                    // Extract resource ID from URL
                    var m = a.href.match(/[?&]id=(\\d+)/);
                    var rid = m ? m[1] : '';
                    items.push({text: text.substring(0, 80), href: a.href, id: rid});
                }
            });
            if(items.length > 0) sections.push({title: title, items: items});
        });
        return JSON.stringify(sections);
    })()
    """, cmd_id=61)

    try:
        sections = json.loads(result)
    except (json.JSONDecodeError, TypeError):
        print("Could not parse course resources.")
        return

    if not sections:
        print(f"No resources found for course {course_id}.")
        return

    print(f"Resources for course {course_id}:\n")
    for sec in sections:
        print(f"[{sec['title']}]")
        for item in sec['items']:
            rid = f"  (id={item['id']})" if item['id'] else ""
            print(f"  • {item['text']}{rid}")
        print()


async def cmd_download(ws):
    """Download a file resource by its Moodle resource ID."""
    if not ARGS:
        print("Usage: download <resource_id> [output_dir]", file=sys.stderr)
        sys.exit(1)

    resource_id = ARGS[0]
    out_dir = ARGS[1] if len(ARGS) > 1 else "/tmp/moodle_files"

    # Validate resource_id is numeric
    if not resource_id.isdigit():
        print(f"ERROR: resource_id must be a number, got: {resource_id}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(out_dir, exist_ok=True)
    resource_url = f"https://moodle.innopolis.university/mod/resource/view.php?id={resource_id}"

    # Enable Network tracking before navigating
    await cdp(ws, "Network.enable", {}, cmd_id=70)

    # Set up a listener for network requests — navigate and capture pluginfile URL
    pluginfile_url = None

    # Send navigate, then drain events for a few seconds watching for pluginfile
    nav_msg = {"id": 71, "method": "Page.navigate", "params": {"url": resource_url}}
    await ws.send(json.dumps(nav_msg))

    deadline = asyncio.get_event_loop().time() + 8
    while asyncio.get_event_loop().time() < deadline:
        try:
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=1))
        except asyncio.TimeoutError:
            continue
        method = msg.get("method", "")
        if method in ("Network.requestWillBeSent", "Network.responseReceived"):
            params = msg.get("params", {})
            url = (params.get("request") or params.get("response") or {}).get("url", "")
            if "pluginfile" in url or any(url.lower().endswith(ext) for ext in (".pdf", ".pptx", ".ppt", ".ipynb", ".zip", ".docx")):
                pluginfile_url = url
                break

    if not pluginfile_url:
        # Fallback: check page links
        links_json = await js(ws, """
        JSON.stringify(Array.from(document.querySelectorAll('a[href]'))
            .map(a => a.href)
            .filter(h => h.includes('pluginfile') ||
                         /\\.(pdf|pptx|ppt|ipynb|zip|docx)/.test(h.toLowerCase())))
        """, cmd_id=72)
        try:
            links = json.loads(links_json or "[]")
            if links:
                pluginfile_url = links[0]
        except (json.JSONDecodeError, TypeError):
            pass

    if not pluginfile_url:
        print(f"ERROR: Could not find download URL for resource {resource_id}.", file=sys.stderr)
        sys.exit(1)

    # Get cookies
    cookies_result = await cdp(ws, "Network.getAllCookies", {}, cmd_id=73)
    cookies = cookies_result.get("cookies", [])
    moodle_cookies = [c for c in cookies if "innopolis.university" in c.get("domain", "")]
    cookie_header = "; ".join(f"{c['name']}={c['value']}" for c in moodle_cookies)

    # Download
    print(f"Downloading: {pluginfile_url}", file=sys.stderr)
    req = urllib.request.Request(pluginfile_url, headers={
        "Cookie": cookie_header,
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    })
    with urllib.request.urlopen(req, timeout=60) as resp:
        content_disp = resp.headers.get("Content-Disposition", "")
        # Extract filename
        filename = f"moodle_resource_{resource_id}"
        if "filename*=UTF-8''" in content_disp:
            filename = urllib.parse.unquote(content_disp.split("filename*=UTF-8''")[-1].strip())
        elif 'filename="' in content_disp:
            filename = content_disp.split('filename="')[1].rstrip('"')
        else:
            # Guess from URL
            url_path = pluginfile_url.split("?")[0]
            filename = urllib.parse.unquote(url_path.split("/")[-1]) or filename

        filepath = os.path.join(out_dir, filename)
        data = resp.read()
        with open(filepath, "wb") as f:
            f.write(data)

    print(filepath)  # stdout: just the path, for piping


async def main():
    ws_url = await get_tab_ws()
    async with websockets.connect(ws_url, max_size=10 * 1024 * 1024) as ws:
        await cdp(ws, "Page.enable", {}, cmd_id=1)
        await cdp(ws, "Runtime.enable", {}, cmd_id=2)

        await login(ws)

        if CMD == "courses":
            await cmd_courses(ws)
        elif CMD == "lectures":
            await cmd_lectures(ws)
        elif CMD == "download":
            await cmd_download(ws)
        else:
            await cmd_deadlines(ws)


if __name__ == "__main__":
    asyncio.run(main())
