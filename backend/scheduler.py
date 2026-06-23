"""Cron-style scheduler — fires prompts into Lumi at scheduled times.

A single background thread wakes every TICK_SEC, and for each enabled job whose cron
schedule has come due since the last check, it invokes the registered action (normally
`assistant.send_text`) so Lumi runs a full turn and speaks the response.

Jobs accept either a full 5-field cron expression ("30 7 * * 1-5") or a friendly
"HH:MM" form with optional weekdays ("07:30 on mon,fri") — the latter is normalised to
cron via `to_cron()`. Jobs persist to a JSON file so they survive restarts.
"""

import json
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime

from croniter import croniter

from . import events

TICK_SEC = 20
_STORE = os.path.join(os.path.dirname(__file__), "schedules.json")

# Friendly weekday names → cron day-of-week numbers (0/7 = Sunday for croniter).
_DOW = {
    "sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6,
    "sunday": 0, "monday": 1, "tuesday": 2, "wednesday": 3, "thursday": 4,
    "friday": 5, "saturday": 6,
}


@dataclass
class Job:
    prompt: str
    cron: str
    label: str = ""
    enabled: bool = True
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    created_at: float = field(default_factory=time.time)
    last_run: float | None = None

    def next_run(self, after: datetime | None = None) -> float:
        # get_next(datetime) is timezone-correct for naive local datetimes (unlike the
        # float form, which assumes UTC); .timestamp() then gives true unix seconds.
        dt = croniter(self.cron, after or datetime.now()).get_next(datetime)
        return dt.timestamp()


_jobs: dict[str, Job] = {}
_lock = threading.Lock()
_action = None  # set via start(); called with the job prompt when a job fires
_thread: threading.Thread | None = None
_stop = threading.Event()
_last_tick: datetime | None = None  # end of the last window we evaluated


# ---------------------------------------------------------------------------
# Schedule parsing
# ---------------------------------------------------------------------------
def to_cron(when: str) -> str:
    """Normalise a schedule string to a 5-field cron expression.

    Accepts a raw cron expression as-is, or a friendly form:
      "07:30"                 → every day at 7:30am
      "7:30am"                → every day at 7:30am
      "07:30 on mon,wed,fri"  → those weekdays at 7:30
      "18:00 weekdays"        → Mon–Fri at 6pm

    Raises ValueError if it can't be parsed.
    """
    when = when.strip()

    # Already a cron expression (5 space-separated fields)?
    parts = when.split()
    if len(parts) == 5 and any(c in when for c in "*/,-") or (
        len(parts) == 5 and all(p.isdigit() or p == "*" for p in parts)
    ):
        if croniter.is_valid(when):
            return when

    # Friendly form: "<time>[ on <days>]" / "<time> weekdays/weekends/daily".
    lower = when.lower()
    time_part, _, day_part = lower.partition(" on ")
    if not day_part:
        # No explicit "on" — peel a trailing day keyword off the time part.
        toks = time_part.split()
        time_part = toks[0]
        day_part = " ".join(toks[1:])

    hour, minute = _parse_clock(time_part)
    dow = _parse_days(day_part)
    return f"{minute} {hour} * * {dow}"


def _parse_clock(s: str) -> tuple[int, int]:
    s = s.strip().lower()
    meridiem = ""
    if s.endswith("am") or s.endswith("pm"):
        meridiem = s[-2:]
        s = s[:-2].strip()
    # Accept "HH:MM" or an hour-only form like "6", "6pm", "18".
    try:
        if ":" in s:
            h_str, m_str = s.split(":", 1)
            hour, minute = int(h_str), int(m_str)
        else:
            hour, minute = int(s), 0
    except ValueError:
        raise ValueError(f"Could not parse time from {s!r} (expected HH:MM or e.g. 6pm)")
    if meridiem == "pm" and hour < 12:
        hour += 12
    elif meridiem == "am" and hour == 12:
        hour = 0
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Time out of range: {hour}:{minute}")
    return hour, minute


def _parse_days(s: str) -> str:
    s = s.strip().lower()
    if not s or s in ("daily", "everyday", "every day", "all"):
        return "*"
    if s in ("weekday", "weekdays"):
        return "1-5"
    if s in ("weekend", "weekends"):
        return "0,6"
    nums = []
    for tok in s.replace(" and ", ",").replace(" ", ",").split(","):
        tok = tok.strip()
        if not tok:
            continue
        if tok not in _DOW:
            raise ValueError(f"Unknown day: {tok!r}")
        nums.append(str(_DOW[tok]))
    return ",".join(nums) if nums else "*"


def describe(cron: str) -> str:
    """Best-effort human description of a cron expression for the UI."""
    try:
        minute, hour, dom, mon, dow = cron.split()
    except ValueError:
        return cron
    if dom == "*" and mon == "*" and minute.isdigit() and hour.isdigit():
        t = f"{int(hour):02d}:{int(minute):02d}"
        days = {
            "*": "every day", "1-5": "weekdays", "0,6": "weekends",
        }.get(dow)
        if days is None:
            names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
            try:
                days = ", ".join(names[int(d) % 7] for d in dow.split(","))
            except ValueError:
                days = f"days {dow}"
        return f"{t} {days}"
    return cron


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def _load() -> None:
    if not os.path.exists(_STORE):
        return
    try:
        with open(_STORE) as f:
            raw = json.load(f)
        with _lock:
            _jobs.clear()
            for d in raw:
                _jobs[d["id"]] = Job(**d)
    except Exception:
        pass  # corrupt/legacy file — start empty rather than crash


def _save() -> None:
    with _lock:
        data = [asdict(j) for j in _jobs.values()]
    tmp = _STORE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _STORE)


# ---------------------------------------------------------------------------
# Public API (used by tools, REST endpoints)
# ---------------------------------------------------------------------------
def view() -> list[dict]:
    """Serializable job list (sorted by next fire time) for the API and snapshot."""
    with _lock:
        jobs = list(_jobs.values())
    out = []
    for j in jobs:
        d = asdict(j)
        d["when"] = describe(j.cron)
        try:
            d["next_run"] = j.next_run() if j.enabled else None
        except Exception:
            d["next_run"] = None
        out.append(d)
    out.sort(key=lambda d: (d["next_run"] is None, d["next_run"] or 0))
    return out


def _broadcast() -> None:
    events.emit("schedules", jobs=view())


def add(when: str, prompt: str, label: str = "") -> Job:
    """Create a job. `when` may be cron or a friendly time; raises ValueError if invalid."""
    cron = to_cron(when)
    job = Job(prompt=prompt.strip(), cron=cron, label=label.strip())
    with _lock:
        _jobs[job.id] = job
    _save()
    _broadcast()
    return job


def update(
    job_id: str,
    when: str | None = None,
    prompt: str | None = None,
    label: str | None = None,
) -> Job | None:
    """Edit an existing job in place. Only the provided fields change. Changing `when`
    re-parses the schedule and resets last_run so the new time fires cleanly. Returns the
    updated Job, or None if no such job. Raises ValueError on an invalid schedule."""
    cron = to_cron(when) if when is not None else None  # validate before mutating
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return None
        if cron is not None:
            job.cron = cron
            job.last_run = None
        if prompt is not None:
            job.prompt = prompt.strip()
        if label is not None:
            job.label = label.strip()
    _save()
    _broadcast()
    return job


def delete(job_id: str) -> bool:
    with _lock:
        existed = _jobs.pop(job_id, None) is not None
    if existed:
        _save()
        _broadcast()
    return existed


def set_enabled(job_id: str, enabled: bool) -> bool:
    with _lock:
        job = _jobs.get(job_id)
        if job:
            job.enabled = enabled
    if job:
        _save()
        _broadcast()
        return True
    return False


# ---------------------------------------------------------------------------
# Scheduler loop
# ---------------------------------------------------------------------------
def _run_due(since: datetime, now: datetime) -> None:
    """Fire every enabled job with a scheduled time in the window (since, now].

    Anchoring each search at `max(last_run, since)` keeps the windows gap-free across
    ticks while ensuring a job never fires twice for the same scheduled time.
    """
    with _lock:
        jobs = list(_jobs.values())
    fired = False
    for job in jobs:
        if not job.enabled:
            continue
        last = datetime.fromtimestamp(job.last_run) if job.last_run else since
        anchor = max(last, since)
        try:
            due = croniter(job.cron, anchor).get_next(datetime)
        except Exception:
            continue
        if due <= now:
            job.last_run = due.timestamp()
            fired = True
            events.emit("schedule_fired", id=job.id, label=job.label or job.prompt)
            if _action:
                try:
                    _action(job.prompt)
                except Exception:
                    pass
    if fired:
        _save()
        _broadcast()


def _loop() -> None:
    global _last_tick
    # Start the first window at "now" so jobs whose time already passed before startup
    # don't fire a burst on boot.
    _last_tick = datetime.now()
    while not _stop.wait(TICK_SEC):
        now = datetime.now()
        _run_due(_last_tick, now)
        _last_tick = now


def start(action) -> None:
    """Load persisted jobs and start the ticking thread. `action(prompt)` fires a job."""
    global _action, _thread
    _action = action
    _load()
    if _thread and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, daemon=True)
    _thread.start()


def stop() -> None:
    _stop.set()


if __name__ == "__main__":
    # Manual smoke test of the parser.
    for w in ["07:30", "7:30am", "6:00pm weekdays", "09:15 on mon,wed,fri",
              "30 7 * * 1-5", "*/15 * * * *"]:
        c = to_cron(w)
        print(f"{w!r:28} -> {c!r:18} ({describe(c)})")
