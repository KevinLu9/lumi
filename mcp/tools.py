from datetime import datetime
import math
import threading
import requests

_timer_callback = None
_clear_history_callback = None


def register_timer_callback(fn):
    global _timer_callback
    _timer_callback = fn


def register_clear_history_callback(fn):
    global _clear_history_callback
    _clear_history_callback = fn


def get_time() -> str:
    """Get the current date and time."""
    return datetime.now().strftime("%A, %d %B %Y, %I:%M %p")


def get_weather(location: str) -> str:
    """Get the current weather for a city or location.

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
        current = data["current_condition"][0]
        desc = current["weatherDesc"][0]["value"]
        temp_c = current["temp_C"]
        feels_c = current["FeelsLikeC"]
        humidity = current["humidity"]
        return f"{location}: {desc}, {temp_c}°C (feels like {feels_c}°C), humidity {humidity}%"
    except Exception as e:
        return f"Could not get weather for {location}: {e}"


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


def reset_chat() -> str:
    """Clear Lumi's conversation history and start a fresh session."""
    if _clear_history_callback:
        _clear_history_callback()
    return "Chat history cleared."


TOOL_FNS: dict = {
    "get_time": get_time,
    "get_weather": get_weather,
    "calculate": calculate,
    "set_timer": set_timer,
    "reset_chat": reset_chat,
}

# OpenAI / Groq JSON schema format — also used to build Gemini declarations manually.
TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Get the current date and time.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a city or location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name or location, e.g. 'Sydney' or 'New York'.",
                    }
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a mathematical expression and return the result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "A math expression such as '2 + 2', 'sqrt(16)', or 'sin(pi / 2)'.",
                    }
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_timer",
            "description": "Set a countdown timer that will announce when it finishes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "seconds": {
                        "type": "integer",
                        "description": "How many seconds to wait before the timer fires.",
                    },
                    "label": {
                        "type": "string",
                        "description": "A short name for the timer, e.g. 'pasta' or 'meeting'.",
                    },
                },
                "required": ["seconds"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reset_chat",
            "description": "Clear Lumi's conversation history and start a fresh session.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


if __name__ == "__main__":
    print("get_time:", get_time())
    print("calculate 2+2:", calculate("2+2"))
    print("calculate sqrt(144):", calculate("sqrt(144)"))
    print("weather Sydney:", get_weather("Sydney"))
    print("set_timer 3s:", set_timer(3, "test"))
    import time; time.sleep(4)
