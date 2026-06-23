from datetime import datetime
import math
import threading
import requests

from ._registry import Registry

registry = Registry()
DESCRIPTION = "Core utilities: time, weather forecast, calculator, timers."

_timer_callback = None
_clear_history_callback = None


def register_timer_callback(fn):
    global _timer_callback
    _timer_callback = fn


def register_clear_history_callback(fn):
    global _clear_history_callback
    _clear_history_callback = fn


@registry.tool
def get_time() -> str:
    """Get the current date and time."""
    return datetime.now().strftime("%A, %d %B %Y, %I:%M %p")


@registry.tool
def get_forecast(location: str) -> str:
    """Get the 3-day weather forecast for a city or location.

    Also renders a forecast widget in the UI. Use this whenever the user asks about the
    weather — current conditions are day 1 of the forecast.

    Args:
        location: City name or location, e.g. 'Sydney' or 'New York'.
    """
    try:
        resp = requests.get(
            f"https://wttr.in/{requests.utils.quote(location)}",
            params={"format": "j1"},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        forecast = []
        for day in data["weather"][:3]:
            # The midday entry (time '1200') is the most representative for the day.
            hourly = day["hourly"]
            midday = next((h for h in hourly if h["time"] == "1200"), hourly[len(hourly) // 2])
            forecast.append({
                "date": day["date"],                                          # ISO yyyy-mm-dd
                "day": datetime.strptime(day["date"], "%Y-%m-%d").strftime("%a"),
                "min": int(day["mintempC"]),
                "max": int(day["maxtempC"]),
                "desc": midday["weatherDesc"][0]["value"].strip(),
                "code": int(midday["weatherCode"]),                           # WWO condition code
                "rain": int(midday["chanceofrain"]),
            })

        # Side-channel the structured forecast to the UI for the weather widget.
        from .. import events
        events.emit("weather", location=location, days=forecast)

        lines = [
            f"{d['day']}: {d['desc']}, {d['min']}–{d['max']}°C, {d['rain']}% chance of rain"
            for d in forecast
        ]
        return f"{location} forecast — " + "; ".join(lines)
    except Exception as e:
        return f"Could not get forecast for {location}: {e}"


@registry.tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression and return the result.

    Args:
        expression: A math expression such as '2 + 2', 'sqrt(16)', or 'sin(pi / 2)'.
    """
    safe_ns = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
    safe_ns.update({"abs": abs, "round": round})
    try:
        result = eval(expression, {"__builtins__": {}}, safe_ns)
        return str(result)
    except Exception as e:
        return f"Error: {e}"


@registry.tool
def set_timer(seconds: int, label: str = "Timer") -> str:
    """Set a countdown timer that will announce when it finishes.

    Args:
        seconds: How many seconds to wait before the timer fires.
        label: A short name for the timer, e.g. 'pasta' or 'meeting'.
    """
    def _fire():
        if _timer_callback:
            _timer_callback(label)

    threading.Timer(seconds, _fire).start()
    return f"Timer set for {seconds} seconds: {label}"


@registry.tool
def reset_chat() -> str:
    """Clear Lumi's conversation history and start a fresh session."""
    if _clear_history_callback:
        _clear_history_callback()
    return "Chat history cleared."


@registry.tool
def find_tools(pattern: str) -> str:
    """Load extra tools so you can use them. Lumi starts with only a few tools; call this
    to bring in more on demand. The matched tools stay available for the rest of the
    conversation. Check the list of loadable tool modules in your instructions first.

    Args:
        pattern: A regular expression matched against tool module names and tool names,
            e.g. 'spotify' to load all music tools, 'light' for smart lights, or
            'light_set.*' to load just specific ones.
    """
    from . import registry as _registry_mod
    return _registry_mod.activate_matching(pattern)


if __name__ == "__main__":
    print("get_time:", get_time())
    print("calculate 2+2:", calculate("2+2"))
    print("calculate sqrt(144):", calculate("sqrt(144)"))
    print("forecast Sydney:", get_forecast("Sydney"))
    print("set_timer 3s:", set_timer(3, "test"))
    import time; time.sleep(4)
