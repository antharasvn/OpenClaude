#!/usr/bin/env python3
"""Shared helpers for OpenClaude daily report runners.

Correctness contracts:
- events_* and events_intraday_* ranges are mutually exclusive (no double-count).
- Display timestamps use an explicit IANA timezone.
- DoD/WoW helpers operate on counts (callers should not pct-diff rates as primary).
- Telegram credentials prefer env vars over hardcoded fallbacks.
"""
from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Prefer env; fallback keeps existing cron working until secrets are rotated out of code.
DEFAULT_BOT_TOKEN = os.environ.get(
    "AAA_BOT_TOKEN",
    os.environ.get("TELEGRAM_BOT_TOKEN", "8628864855:AAFWSgQCzUIGNtBK1dQk28rCJ7rqBo3v0zU"),
)
DEFAULT_CHAT_ID = os.environ.get("AAA_CHAT_ID", "-5201056067")


def run(cmd, input_text=None, timeout=300):
    return subprocess.run(
        cmd, input=input_text, text=True, capture_output=True, check=False, timeout=timeout
    )


def bq_query(project_id: str, sql: str) -> list[dict]:
    cp = run(
        [
            "bq",
            "query",
            "--use_legacy_sql=false",
            f"--project_id={project_id}",
            "--format=json",
            "--max_rows=100000",
        ],
        input_text=sql,
        timeout=600,
    )
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr or cp.stdout or "bq query failed")
    raw = (cp.stdout or "").strip()
    if not raw:
        return []
    return json.loads(raw)


def send_telegram(
    text: str,
    bot_token: str | None = None,
    chat_id: str | None = None,
    timeout: int = 30,
) -> dict:
    token = bot_token or DEFAULT_BOT_TOKEN
    chat = chat_id or DEFAULT_CHAT_ID
    payload = json.dumps({"chat_id": chat, "text": text, "parse_mode": ""}).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def pct(cur, base) -> str:
    """Percent change of counts. Returns N/A when base is 0."""
    try:
        cur_f = float(cur)
        base_f = float(base)
    except (TypeError, ValueError):
        return "N/A"
    if not base_f:
        return "N/A"
    return f"{((cur_f - base_f) / base_f) * 100:+.0f}%"


def get_conversion_emoji(rate) -> str:
    try:
        r = float(rate)
    except (TypeError, ValueError):
        return "🔴"
    if r > 50:
        return "🟣"
    if r > 30:
        return "🔵"
    if r > 20:
        return "🟢"
    if r > 10:
        return "✅"
    if r > 5:
        return "⚠️"
    if r > 2:
        return "🟠"
    return "🔴"


def get_onboarding_emoji(rate) -> str:
    try:
        r = float(rate)
    except (TypeError, ValueError):
        return "🔴"
    if r >= 95:
        return "🟣"
    if r >= 90:
        return "🔵"
    if r >= 85:
        return "🟢"
    if r >= 80:
        return "✅"
    if r >= 70:
        return "⚠️"
    if r >= 60:
        return "🟠"
    return "🔴"


def safe_rate(num, den, digits=1) -> float:
    try:
        n, d = float(num), float(den)
    except (TypeError, ValueError):
        return 0.0
    if d <= 0:
        return 0.0
    return round(n / d * 100, digits)


def rolling_windows(tz_name: str = "America/New_York") -> dict[str, Any]:
    """Build rolling 24h / DoD / WoW microsecond windows + table suffixes."""
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    now_epoch = int(now.timestamp())
    return {
        "tz_name": tz_name,
        "now": now,
        "now_epoch": now_epoch,
        "now_us": now_epoch * 1_000_000,
        "h24_us": (now_epoch - 86400) * 1_000_000,
        "h48_us": (now_epoch - 172800) * 1_000_000,
        "h168_us": (now_epoch - 604800) * 1_000_000,
        "h192_us": (now_epoch - 691200) * 1_000_000,
        "display_date": now.strftime("%Y-%m-%d"),
        "display_time": now.strftime("%H:%M"),
        "tz_label": _tz_label(tz_name),
        "suffix_end": now.strftime("%Y%m%d"),
        "suffix_start": (now - timedelta(days=2)).strftime("%Y%m%d"),
        "suffix_week_start": (now - timedelta(days=9)).strftime("%Y%m%d"),
        "suffix_week_end": (now - timedelta(days=6)).strftime("%Y%m%d"),
        "suffix_7d_start": (now - timedelta(days=8)).strftime("%Y%m%d"),
        "suffix_3d_start": (now - timedelta(days=4)).strftime("%Y%m%d"),
        "suffix_end_7d": (now + timedelta(days=7)).strftime("%Y%m%d"),
    }


def _tz_label(tz_name: str) -> str:
    mapping = {
        "America/New_York": "ET",
        "Asia/Saigon": "ICT",
        "Asia/Ho_Chi_Minh": "ICT",
        "Europe/Warsaw": "CET",
        "UTC": "UTC",
    }
    return mapping.get(tz_name, tz_name.split("/")[-1])


def events_cte(
    project_id: str,
    dataset_id: str,
    suffix_start: str,
    suffix_end: str,
    alias: str = "all_events",
    columns: str = "*",
) -> str:
    """Mutually exclusive daily + intraday CTE.

    Intraday rows are kept only for table suffixes strictly after the latest
    finalized daily `events_YYYYMMDD` in the requested range — prevents double-count.
    """
    fq_daily = f"`{project_id}.{dataset_id}.events_*`"
    fq_intra = f"`{project_id}.{dataset_id}.events_intraday_*`"
    # SELECT list for both sides must match. When columns is '*', use SELECT *.
    if columns.strip() == "*":
        daily_sel = f"SELECT * FROM {fq_daily}"
        intra_sel = f"SELECT i.* FROM {fq_intra} i"
    else:
        daily_sel = f"SELECT {columns} FROM {fq_daily}"
        # qualify columns for alias i when not *
        col_list = ", ".join(c.strip() for c in columns.split(","))
        # For non-star, still select from i with same names
        intra_sel = f"SELECT {col_list} FROM {fq_intra} i"
    return f"""{alias} AS (
  {daily_sel}
  WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  {intra_sel}
  WHERE i._TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
    AND i._TABLE_SUFFIX > IFNULL((
      SELECT MAX(_TABLE_SUFFIX)
      FROM {fq_daily}
      WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
    ), '00000000')
)"""


def traffic_bucket_sql(alias: str = "e") -> str:
    """SQL CASE for organic / paid / unattributed from GA4 traffic_source.medium."""
    # traffic_source is a RECORD on the event row
    return f"""CASE
    WHEN {alias}.traffic_source.medium = 'cpc' THEN 'paid'
    WHEN {alias}.traffic_source.medium IS NULL THEN 'unattributed'
    ELSE 'organic'
  END"""


def platform_sql(alias: str = "e") -> str:
    return f"""CASE
    WHEN {alias}.device.category = 'tablet' AND {alias}.device.operating_system = 'iOS' THEN 'iPad'
    WHEN {alias}.device.category = 'mobile' AND {alias}.device.operating_system = 'iOS' THEN 'iPhone'
    WHEN {alias}.device.operating_system = 'Android' THEN 'Android'
    WHEN {alias}.device.category = 'desktop'
      OR {alias}.device.operating_system IN ('Windows', 'Macintosh', 'Linux', 'Chrome OS') THEN 'Web'
    ELSE 'Other'
  END"""


def format_country_lines(rows, count_key: str = "new_users", limit: int = 10) -> str:
    lines = []
    for r in rows[:limit]:
        lines.append(f"    {r.get('country') or '?'}: {int(r.get(count_key, 0) or 0)}")
    return "\n".join(lines) if lines else "    (no data)"


def format_country_conversion(
    top_rows: list[dict],
    global_shown: int,
    global_converted: int,
    limit: int = 10,
) -> str:
    """TOTAL uses global counts; list is top N by paywall volume."""
    rate = safe_rate(global_converted, global_shown)
    lines = [
        f"    TOTAL: {global_shown}→{global_converted} ({rate}%) {get_conversion_emoji(rate)}",
        "    ─────────────────────",
    ]
    for r in top_rows[:limit]:
        country = r.get("country") or "?"
        shown = int(r.get("paywall_shown", 0) or 0)
        conv = int(r.get("converted", 0) or 0)
        rrate = float(r.get("conversion_rate") or safe_rate(conv, shown))
        lines.append(f"    {country}: {shown}→{conv} ({rrate}%) {get_conversion_emoji(rrate)}")
    if len(lines) == 2:
        lines.append("    (no data)")
    return "\n".join(lines)


def format_source_split(rows: list[dict]) -> str:
    """rows: [{source, new_users}]"""
    buckets = {"organic": 0, "paid": 0, "unattributed": 0}
    for r in rows:
        src = (r.get("source") or "unattributed").lower()
        if src not in buckets:
            src = "unattributed"
        buckets[src] = int(r.get("new_users", 0) or 0)
    total = sum(buckets.values()) or 1
    parts = []
    for k in ("organic", "paid", "unattributed"):
        n = buckets[k]
        parts.append(f"{k} {n} ({safe_rate(n, total):.0f}%)")
    return " · ".join(parts)


def format_platform_line(rows: list[dict], count_key: str = "users") -> str:
    order = ["iPhone", "iPad", "Android", "Web", "Other"]
    counts = {p: 0 for p in order}
    for r in rows:
        p = r.get("platform") or "Other"
        if p not in counts:
            p = "Other"
        counts[p] += int(r.get(count_key, 0) or 0)
    return " · ".join(f"{p} {counts[p]}" for p in order if counts[p] or p != "Other")


def format_experiments(exp_metrics: list[dict], style: str = "conv") -> str:
    """style: 'conv' => B:Nu/X%  |  'full' => users/done%/trial%/conv%"""
    if not exp_metrics:
        return "    No running experiments"
    exp_data: dict[str, dict] = {}
    for row in exp_metrics:
        exp_id = str(row.get("exp_id", "?"))
        if exp_id not in exp_data:
            exp_data[exp_id] = {"name": row.get("exp_name", exp_id), "variants": []}
        exp_data[exp_id]["variants"].append(row)
    lines = []
    for exp_id, data in exp_data.items():
        var_strs = []
        for v in sorted(data["variants"], key=lambda x: str(x.get("variant", "0"))):
            variant = str(v.get("variant", "?"))
            paywall = int(v.get("paywall", 0) or 0)
            conv = float(v.get("conv_rate", 0) or 0)
            vname = "B" if variant in ("0", "Baseline", "baseline") else f"V{variant}"
            if style == "full":
                done = float(v.get("completion", 0) or 0)
                trial = float(v.get("trial_rate", 0) or 0)
                var_strs.append(
                    f"{vname}:{paywall}u/{done:.0f}%/{trial:.0f}%/{conv:.0f}%{get_conversion_emoji(conv)}"
                )
            else:
                var_strs.append(f"{vname}:{paywall}u/{conv:.0f}%{get_conversion_emoji(conv)}")
        lines.append(f"    {exp_id}: {' | '.join(var_strs)}")
    return "\n".join(lines)


def exp_user_property_keys(exp_id: str) -> list[str]:
    """Both legacy firebase_exp_N and newer firebase_exp_abt_N forms."""
    eid = str(exp_id).strip()
    keys = [f"firebase_exp_{eid}"]
    if eid.startswith("abt_"):
        keys.append(f"firebase_exp_{eid}")  # already abt form
        # also bare numeric if abt_88 → try 88? skip
    else:
        keys.append(f"firebase_exp_abt_{eid}")
    # de-dupe preserve order
    seen = set()
    out = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def get_running_experiments(project_id: str) -> list[dict]:
    import shutil

    firebase = shutil.which("firebase")
    if not firebase:
        for path in (
            "/opt/homebrew/bin/firebase",
            os.path.expanduser("~/.nvm/versions/node/v24.12.0/bin/firebase"),
        ):
            if os.path.exists(path):
                firebase = path
                break
    if not firebase:
        return []
    result = run([firebase, "remoteconfig:experiments:list", "--project", project_id, "--pageSize", "0"])
    experiments = []
    for line in (result.stdout or "").split("\n"):
        if "│ RUNNING │" not in line:
            continue
        parts = [p.strip() for p in line.split("│") if p.strip()]
        if len(parts) >= 2:
            experiments.append({"id": parts[0], "name": parts[1][:35]})
    return experiments


def save_report(base: Path, report: str, report_path: Optional[Path] = None, display_date: str = "") -> None:
    base.mkdir(parents=True, exist_ok=True)
    (base / "latest_report.txt").write_text(report + "\n")
    if report_path is not None:
        report_path.mkdir(parents=True, exist_ok=True)
        name = f"{display_date}.md" if display_date else "latest.md"
        (report_path / name).write_text(report + "\n")
