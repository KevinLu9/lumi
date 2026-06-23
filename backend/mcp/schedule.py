"""Scheduling tools: let Lumi create and manage recurring scheduled prompts.

A scheduled job fires its prompt back into Lumi at the given time, so the user can say
"every morning at 7 tell me the weather" and hear the answer each day.
"""

from ._registry import Registry
from .. import scheduler

registry = Registry()
DESCRIPTION = (
    "Schedule recurring prompts to run and speak. Any cron schedule, from a daily "
    "time to intervals like every minute or every 5 minutes."
)


@registry.tool
def schedule_create(when: str, prompt: str, label: str = "") -> str:
    """Schedule a prompt to run automatically on a recurring schedule.

    Any cron schedule is supported, including high-frequency intervals, so 'every
    minute' or 'every 5 minutes' is fine, not just daily times. The prompt runs through
    Lumi as if the user asked it, so phrase it as an instruction, e.g. 'Give me today's
    weather forecast for Sydney.'

    Args:
        when: When to run. Either a 5-field cron expression
            (minute hour day-of-month month day-of-week) such as '* * * * *' for every
            minute, '*/5 * * * *' for every 5 minutes, or '30 7 * * 1-5' for 7:30am on
            weekdays; or a friendly time like '07:30', '7:30am', '6pm weekdays', or
            '09:15 on mon,wed,fri'.
        prompt: What Lumi should do when it fires, phrased as a request.
        label: Optional short name for the schedule, e.g. 'morning briefing'.
    """
    try:
        job = scheduler.add(when, prompt, label)
    except ValueError as e:
        return f"Couldn't understand the schedule '{when}': {e}"
    return f"Scheduled '{job.label or prompt}' for {scheduler.describe(job.cron)} (id {job.id})."


@registry.tool
def schedule_list() -> str:
    """List all scheduled prompts and when they next run."""
    jobs = scheduler.view()
    if not jobs:
        return "No schedules set."
    lines = []
    for j in jobs:
        state = "" if j["enabled"] else " (disabled)"
        name = j["label"] or j["prompt"]
        lines.append(f"[{j['id']}] {name}: {j['when']}{state}")
    return "; ".join(lines)


@registry.tool
def schedule_delete(schedule_id: str) -> str:
    """Delete a scheduled prompt by its id.

    Args:
        schedule_id: The id of the schedule to remove (from schedule_list).
    """
    if scheduler.delete(schedule_id):
        return f"Deleted schedule {schedule_id}."
    return f"No schedule with id {schedule_id}."
