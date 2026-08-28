"""Cron job scheduler for OpenClaude bot."""

import asyncio
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from bot.config import get_agent_cli
from bot.logging_setup import infra_logger as logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class JobScheduler:
    TICK_ID = "_clock-tick"

    async def _tick(self):
        """No-op; exists so APScheduler re-arms its timer every 60 s."""

    def __init__(self, bot=None, config_path=None):
        self.bot = bot
        self.config_path = Path(config_path or PROJECT_ROOT / "cron" / "jobs.json")
        self.state_path = PROJECT_ROOT / "cron" / "state.json"
        # asyncio timers run on time.monotonic() == mach_absolute_time(), which
        # does NOT advance while macOS sleeps.  APScheduler arms ONE call_later
        # for the earliest job, so every minute the host sleeps between arming
        # and that slot fires it that much late, and past misfire_grace_time the
        # run is dropped.  With only daily jobs loaded the timer is armed ~11 h
        # out (2026-08-29: 65 min of sleep => cleanpro-daily 03:00 ICT never
        # fired; the old hourly job had been re-anchoring it by accident).
        # Fix: a 60 s tick keeps the timer within a minute of wall-clock, and a
        # generous grace runs a slot that fell inside a sleep at wake.
        self.scheduler = AsyncIOScheduler(
            job_defaults={"misfire_grace_time": 6 * 3600, "coalesce": True}
        )
        self.jobs = []
        self.state = {}

    async def start(self):
        self._load_config()
        self._load_state()

        for job in self.jobs:
            if not job.get("enabled", True):
                logger.info("Skipping disabled job: %s", job["id"])
                continue

            schedule = job["schedule"]
            if "cron" in schedule:
                trigger = CronTrigger.from_crontab(
                    schedule["cron"],
                    timezone=schedule.get("timezone", "UTC"),
                )
            elif "interval_seconds" in schedule:
                trigger = IntervalTrigger(seconds=schedule["interval_seconds"])
            else:
                logger.warning("Job %s has no valid schedule, skipping", job["id"])
                continue

            self.scheduler.add_job(
                self._run_job,
                trigger,
                args=[job],
                id=job["id"],
                name=job["name"],
                replace_existing=True,
            )
            logger.info("Registered job: %s (%s)", job["name"], job["id"])

        # Clock tick: see __init__.  Excluded from the job count below so the
        # "started with N jobs" line keeps meaning "N configured jobs".
        self.scheduler.add_job(
            self._tick,
            IntervalTrigger(seconds=60),
            id=self.TICK_ID,
            name="clock tick",
            misfire_grace_time=None,
            replace_existing=True,
        )

        self.scheduler.start()
        n_jobs = len([j for j in self.scheduler.get_jobs() if j.id != self.TICK_ID])
        logger.info("Cron scheduler started with %d jobs", n_jobs)

    async def shutdown(self):
        self.scheduler.shutdown(wait=False)
        self._save_state()
        logger.info("Cron scheduler shut down")

    async def run_job_by_id(self, job_id):
        for job in self.jobs:
            if job["id"] == job_id:
                return await self._run_job(job)
        raise ValueError(f"Job not found: {job_id}")

    def list_jobs(self):
        result = []
        for job in self.jobs:
            state = self.state.get(job["id"], {})
            result.append({
                "id": job["id"],
                "name": job["name"],
                "enabled": job.get("enabled", True),
                "type": job["type"],
                "last_run": state.get("last_run"),
                "last_status": state.get("last_status"),
                "consecutive_errors": state.get("consecutive_errors", 0),
            })
        return result

    async def _run_job(self, job):
        job_id = job["id"]
        logger.info("Running job: %s", job_id)
        try:
            if job["type"] == "script":
                result = await self._run_script(job)
            elif job["type"] == "prompt":
                result = await self._run_prompt(job)
            else:
                raise ValueError(f"Unknown job type: {job['type']}")
            self._on_success(job_id)
            logger.info("Job %s completed successfully", job_id)
            return result
        except Exception as e:
            await self._on_error(job_id, job, e)
            raise

    async def _run_script(self, job):
        script_path = PROJECT_ROOT / job["script"]
        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")

        proc = await asyncio.create_subprocess_exec(
            sys.executable, str(script_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(PROJECT_ROOT),
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
        except asyncio.TimeoutError:
            proc.kill()
            raise TimeoutError(f"Script {job['id']} timed out after 5 min")

        if proc.returncode != 0:
            raise RuntimeError(
                f"Script {job['id']} exited with code {proc.returncode}: "
                f"{stderr.decode()[-500:]}"
            )
        return stdout.decode()[-500:]

    async def _run_prompt(self, job):
        skill_path = PROJECT_ROOT / job["skill"]
        if not skill_path.exists():
            raise FileNotFoundError(f"Skill file not found: {skill_path}")

        prompt = skill_path.read_text()

        # Cron jobs run on the same CLI as chat.  grok names its tools
        # differently, so claude's --allowedTools list would allow-list nothing
        # there; its equivalent is bypassPermissions, with the guard.sh
        # PreToolUse hooks still enforcing.
        if get_agent_cli() == "grok":
            grok_bin = shutil.which("grok") or str(Path.home() / ".grok" / "bin" / "grok")
            argv = [grok_bin, "-p", prompt, "--permission-mode", "bypassPermissions"]
        else:
            claude_bin = Path.home() / ".local" / "bin" / "claude"
            if not claude_bin.exists():
                claude_bin = "claude"  # fall back to PATH
            argv = [
                str(claude_bin),
                "-p", prompt,
                "--allowedTools", "Read,Write,Edit,Bash,Glob,Grep,WebFetch,WebSearch",
            ]

        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(PROJECT_ROOT),
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
        except asyncio.TimeoutError:
            proc.kill()
            # Drain what the CLI printed before the cap fired.  Without this the
            # only prompt-job failures that ever need diagnosing are the ones
            # that leave no diagnostics at all: communicate() never returns on
            # this path, so the stderr of a capped job is destroyed with it.
            tail = ""
            try:
                _, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
                tail = stderr.decode(errors="replace").strip()[-300:]
            except Exception:
                logger.exception("Could not drain stderr for %s", job["id"])
            msg = f"Prompt job {job['id']} timed out after 10 min"
            raise TimeoutError(f"{msg}: {tail}" if tail else msg)

        result = stdout.decode()

        # If job has announce delivery, send result to Telegram
        delivery = job.get("delivery", {})
        announce_chat = delivery.get("announce")
        if announce_chat and result.strip() and self.bot:
            try:
                from bot.telegram_sender import send_rendered_bot
                await send_rendered_bot(self.bot, int(announce_chat), result)
            except Exception:
                logger.exception("Failed to announce result for %s", job["id"])

        return result[-500:]

    def _on_success(self, job_id):
        self.state[job_id] = {
            "last_run": datetime.now(timezone.utc).isoformat(),
            "last_status": "OK",
            "consecutive_errors": 0,
        }
        self._save_state()

    async def _on_error(self, job_id, job, error):
        state = self.state.get(job_id, {"consecutive_errors": 0})
        consecutive = state.get("consecutive_errors", 0) + 1
        self.state[job_id] = {
            "last_run": datetime.now(timezone.utc).isoformat(),
            "last_status": f"ERROR: {error}",
            "consecutive_errors": consecutive,
        }
        self._save_state()
        logger.error("Job %s failed (%dx): %s", job_id, consecutive, error)

        if consecutive >= 3 and self.bot:
            on_error_chat = job.get("delivery", {}).get("on_error")
            if on_error_chat:
                try:
                    from bot.telegram_sender import send_rendered_bot
                    await send_rendered_bot(
                        self.bot,
                        int(on_error_chat),
                        f"**Job `{job['name']}` failed {consecutive}x**\n"
                        f"```\n{str(error)[:300]}\n```",
                    )
                except Exception:
                    logger.exception("Failed to send error alert for %s", job_id)

    def _load_config(self):
        if not self.config_path.exists():
            logger.warning("No cron config at %s", self.config_path)
            self.jobs = []
            return
        with open(self.config_path) as f:
            data = json.load(f)
        self.jobs = data.get("jobs", [])
        logger.info("Loaded %d job definitions", len(self.jobs))

    def _load_state(self):
        if self.state_path.exists():
            try:
                with open(self.state_path) as f:
                    self.state = json.load(f)
            except (json.JSONDecodeError, OSError):
                self.state = {}

    def _save_state(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w") as f:
            json.dump(self.state, f, indent=2)
