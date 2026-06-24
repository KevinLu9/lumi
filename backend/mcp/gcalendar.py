"""Google Calendar tools — read the user's agenda and create events.

Requires GOOGLE_CLIENT_ID in .env and a one-time `python -m backend.mcp.google_auth`
to grant access (shares the same consent as the Gmail tools).
"""

from datetime import datetime, timedelta

from ._registry import Registry

registry = Registry()
REQUIRES_ENV = "GOOGLE_CLIENT_ID"  # only registered when Google is configured
DESCRIPTION = "Read your Google Calendar agenda and create new calendar events."


def _service():
    from . import google_auth
    return google_auth.service("calendar", "v3")


def _rfc3339(dt: datetime) -> str:
    # astimezone() attaches the local offset to a naive datetime (and converts an
    # aware one), giving Calendar the timezone-qualified RFC3339 string it needs.
    return dt.astimezone().isoformat()


def _format_event(ev: dict) -> str:
    start = ev.get("start", {})
    when = start.get("dateTime") or start.get("date") or ""
    label = ev.get("summary", "(no title)")
    if "T" in when:
        try:
            t = datetime.fromisoformat(when).strftime("%a %I:%M %p").lstrip("0")
            return f"{t} — {label}"
        except ValueError:
            pass
    return f"{when} (all day) — {label}" if when else label


def _list(time_min: datetime, time_max: datetime, label: str) -> str:
    from . import google_auth
    try:
        events = _service().events().list(
            calendarId="primary",
            timeMin=_rfc3339(time_min),
            timeMax=_rfc3339(time_max),
            singleEvents=True,
            orderBy="startTime",
            maxResults=20,
        ).execute().get("items", [])
    except google_auth.NotConnectedError as e:
        return str(e)
    except Exception as e:
        return f"Couldn't reach Google Calendar: {e}"
    if not events:
        return f"Nothing on your calendar {label}."
    return f"{label.capitalize()}: " + "; ".join(_format_event(e) for e in events)


@registry.tool
def calendar_today() -> str:
    """List the events on the user's Google Calendar for the rest of today."""
    now = datetime.now()
    end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    return _list(now, end, "today")


@registry.tool
def calendar_upcoming(days: int = 7) -> str:
    """List upcoming events on the user's Google Calendar.

    Args:
        days: How many days ahead to look (default 7).
    """
    now = datetime.now()
    return _list(now, now + timedelta(days=max(1, days)), f"the next {days} day(s)")


@registry.tool
def calendar_create(title: str, start: str, end: str = "") -> str:
    """Create an event on the user's Google Calendar.

    Compute the times from the current date/time (use get_time if unsure) and pass
    them as ISO 8601 strings.

    Args:
        title: The event title, e.g. 'Lunch with Sam'.
        start: Start time as ISO 8601, e.g. '2026-06-25T12:00:00'.
        end: End time as ISO 8601. Defaults to one hour after start if omitted.
    """
    from . import google_auth
    try:
        start_dt = datetime.fromisoformat(start)
    except ValueError:
        return f"I couldn't read the start time '{start}'. Use ISO 8601 like 2026-06-25T12:00:00."
    if end:
        try:
            end_dt = datetime.fromisoformat(end)
        except ValueError:
            return f"I couldn't read the end time '{end}'. Use ISO 8601 like 2026-06-25T13:00:00."
    else:
        end_dt = start_dt + timedelta(hours=1)
    try:
        ev = _service().events().insert(calendarId="primary", body={
            "summary": title,
            "start": {"dateTime": _rfc3339(start_dt)},
            "end": {"dateTime": _rfc3339(end_dt)},
        }).execute()
    except google_auth.NotConnectedError as e:
        return str(e)
    except Exception as e:
        return f"Couldn't create the event: {e}"
    when = start_dt.strftime("%a %d %b, %I:%M %p").replace(" 0", " ")
    return f"Added '{ev.get('summary', title)}' on {when}."


if __name__ == "__main__":
    print(calendar_today())
    print(calendar_upcoming(7))
