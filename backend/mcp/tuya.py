"""Tuya (Smart Life) smart bulb tools — controls one or more color+white bulbs through the
Tuya cloud with tinytuya's Cloud API (works even when the bulbs can't be reached on the LAN,
e.g. behind WiFi AP/client isolation).

Lights are discovered automatically from your linked Smart Life account, so you can target a
specific one by name ("the desk lamp"). Rename bulbs in the Smart Life app to give them
friendly names.

Requires in .env: TUYA_API_REGION, TUYA_API_KEY, TUYA_API_SECRET (and optionally
TUYA_DEVICE_ID as the default light). Get them once by creating a Tuya IoT Cloud project,
linking your Smart Life account, and running `python -m tinytuya wizard`. See the README."""

import os
import json
import colorsys
from dotenv import load_dotenv

from ._registry import Registry

registry = Registry()
REQUIRES_ENV = "TUYA_DEVICE_ID"  # only registered by registry.py when this is set
DESCRIPTION = "Control Tuya/Smart Life smart lights: power, brightness, colour, white temperature."

load_dotenv()

_cloud = None
_lights_cache: dict[str, str] | None = None  # friendly name -> device id

# Tuya category codes that are lights (dj=bulb, dd=strip, dc=string, xdd=ceiling, fwd/tgq=dimmer).
_LIGHT_CATEGORIES = {"dj", "dd", "dc", "xdd", "fwd", "tgq", "tyndj"}

# Friendly color names → (r, g, b). Extend freely.
COLORS: dict[str, tuple[int, int, int]] = {
    "red": (255, 0, 0),
    "orange": (255, 90, 0),
    "yellow": (255, 200, 0),
    "green": (0, 255, 0),
    "lime": (160, 255, 0),
    "cyan": (0, 255, 255),
    "teal": (0, 200, 160),
    "blue": (0, 0, 255),
    "sky": (0, 160, 255),
    "purple": (140, 0, 255),
    "violet": (180, 80, 255),
    "magenta": (255, 0, 255),
    "pink": (255, 80, 180),
    "white": (255, 255, 255),
    "warm white": (255, 180, 100),
}

# Warmth keyword → colour-temperature percentage (0 = warmest, 100 = coolest).
WHITE_TEMPS: dict[str, int] = {
    "warm": 0,
    "soft": 20,
    "neutral": 50,
    "cool": 80,
    "daylight": 100,
}


class LightLookupError(Exception):
    """Raised when a named light can't be resolved; its message is shown to the user."""


def _get_cloud():
    global _cloud
    if _cloud is None:
        import tinytuya
        _cloud = tinytuya.Cloud(
            os.environ["TUYA_API_REGION"],
            os.environ["TUYA_API_KEY"],
            os.environ["TUYA_API_SECRET"],
            os.environ.get("TUYA_DEVICE_ID", ""),
        )
    return _cloud


def _lights(refresh: bool = False) -> dict[str, str]:
    """Map of friendly name -> device id for every light on the account (cached)."""
    global _lights_cache
    if _lights_cache is None or refresh:
        devs = _get_cloud().getdevices(verbose=False) or []
        lights = {
            d["name"]: d["id"]
            for d in devs
            if d.get("id") and d.get("name") and d.get("category") in _LIGHT_CATEGORIES
        }
        # Fall back to all devices if category filtering found nothing.
        if not lights:
            lights = {d["name"]: d["id"] for d in devs if d.get("id") and d.get("name")}
        _lights_cache = lights
    return _lights_cache


def _resolve(name: str = "") -> str:
    """Resolve a (possibly partial) light name to a device id."""
    lights = _lights()
    if not lights:
        raise LightLookupError("I can't find any lights on your Tuya account.")
    if not name:
        if len(lights) == 1:
            return next(iter(lights.values()))
        env_id = os.environ.get("TUYA_DEVICE_ID")
        if env_id and env_id in lights.values():
            return env_id
        raise LightLookupError("Which light? I can control: " + ", ".join(lights))
    q = name.strip().lower()
    for n, i in lights.items():  # exact (case-insensitive) match wins
        if n.lower() == q:
            return i
    matches = [(n, i) for n, i in lights.items() if q in n.lower()]
    if len(matches) == 1:
        return matches[0][1]
    if len(matches) > 1:
        raise LightLookupError(
            f"Several lights match '{name}': " + ", ".join(n for n, _ in matches)
        )
    raise LightLookupError(
        f"I don't see a light called '{name}'. I have: " + ", ".join(lights)
    )


def _fmt_err(e) -> str:
    msg = str(e).lower()
    if any(s in msg for s in ("timed out", "connect", "network", "token", "1004", "1106")):
        return "Couldn't reach the light through the Tuya cloud — check your internet and that the bulb is online in the Smart Life app."
    return f"Light error: {e}"


def _send(device_id: str, commands: list[dict]) -> None:
    """Send DP commands via the cloud; raise on any failure so _fmt_err can handle it."""
    resp = _get_cloud().sendcommand(device_id, {"commands": commands})
    if not isinstance(resp, dict) or not resp.get("success"):
        msg = (resp or {}).get("msg") or (resp or {}).get("Error") or resp
        raise RuntimeError(f"{msg} (code {(resp or {}).get('code') or (resp or {}).get('Err')})")


def _parse_color(color: str) -> tuple[int, int, int] | None:
    color = color.strip().lower()
    if color in COLORS:
        return COLORS[color]
    if color.startswith("#") and len(color) == 7:
        try:
            return (int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16))
        except ValueError:
            return None
    return None


def _rgb_to_tuya_hsv(r: int, g: int, b: int) -> dict:
    """RGB (0–255) → Tuya colour_data_v2 HSV (h 0–360, s/v 0–1000)."""
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return {"h": round(h * 360), "s": round(s * 1000), "v": round(v * 1000)}


def _label(device_id: str) -> str:
    for n, i in _lights().items():
        if i == device_id:
            return n
    return "light"


@registry.tool
def light_list() -> str:
    """List the smart lights available to control, by name."""
    try:
        lights = _lights(refresh=True)
    except Exception as e:
        return _fmt_err(e)
    if not lights:
        return "I can't find any lights on your Tuya account."
    return "I can control these lights: " + ", ".join(lights) + "."


@registry.tool
def light_set_power(on: bool, name: str = "") -> str:
    """Turn a smart light on or off.

    Args:
        on: True to turn the light on, False to turn it off.
        name: Which light (by name); leave empty if there's only one.
    """
    try:
        dev = _resolve(name)
    except LightLookupError as e:
        return str(e)
    try:
        _send(dev, [{"code": "switch_led", "value": bool(on)}])
        return f"Turned {_label(dev)} {'on' if on else 'off'}."
    except Exception as e:
        return _fmt_err(e)


@registry.tool
def light_set_all_power(on: bool) -> str:
    """Turn every smart light on or off at once.

    Args:
        on: True to turn all lights on, False to turn them all off.
    """
    try:
        lights = _lights()
    except Exception as e:
        return _fmt_err(e)
    if not lights:
        return "I can't find any lights on your Tuya account."
    done, failed = [], []
    for label, dev in lights.items():
        try:
            _send(dev, [{"code": "switch_led", "value": bool(on)}])
            done.append(label)
        except Exception:
            failed.append(label)
    word = "on" if on else "off"
    if not failed:
        return f"Turned all lights {word} ({', '.join(done)})."
    if not done:
        return f"Couldn't reach any lights to turn them {word}."
    return f"Turned {', '.join(done)} {word}, but couldn't reach {', '.join(failed)}."


@registry.tool
def light_set_brightness(percent: int, name: str = "") -> str:
    """Set a smart light's brightness.

    Args:
        percent: Brightness from 1 (dimmest) to 100 (brightest).
        name: Which light (by name); leave empty if there's only one.
    """
    try:
        dev = _resolve(name)
    except LightLookupError as e:
        return str(e)
    try:
        pct = max(1, min(100, int(percent)))
        value = max(10, round(pct / 100 * 1000))  # Tuya bright_value_v2 is 10–1000.
        _send(dev, [{"code": "switch_led", "value": True},
                    {"code": "bright_value_v2", "value": value}])
        return f"Set {_label(dev)} brightness to {pct}%."
    except Exception as e:
        return _fmt_err(e)


@registry.tool
def light_set_color(color: str, name: str = "") -> str:
    """Set a smart light's color.

    Args:
        color: A color name such as 'blue', 'warm white', 'pink', or a hex code like '#ff8800'.
        name: Which light (by name); leave empty if there's only one.
    """
    rgb = _parse_color(color)
    if rgb is None:
        return f"I don't know the color '{color}'. Try a name like blue or a hex like #ff8800."
    try:
        dev = _resolve(name)
    except LightLookupError as e:
        return str(e)
    try:
        hsv = _rgb_to_tuya_hsv(*rgb)
        _send(dev, [{"code": "switch_led", "value": True},
                    {"code": "work_mode", "value": "colour"},
                    {"code": "colour_data_v2", "value": json.dumps(hsv)}])
        return f"Set {_label(dev)} to {color}."
    except Exception as e:
        return _fmt_err(e)


@registry.tool(required=["warmth"])
def light_set_white(warmth: str = "neutral", name: str = "") -> str:
    """Switch a smart light to white and set how warm or cool it is.

    Args:
        warmth: One of 'warm', 'soft', 'neutral', 'cool', or 'daylight'.
        name: Which light (by name); leave empty if there's only one.
    """
    key = warmth.strip().lower()
    if key not in WHITE_TEMPS:
        return f"Choose a warmth like warm, neutral, or cool (got '{warmth}')."
    try:
        dev = _resolve(name)
    except LightLookupError as e:
        return str(e)
    try:
        value = round(WHITE_TEMPS[key] / 100 * 1000)  # temp_value_v2 0 (warm) – 1000 (cool).
        _send(dev, [{"code": "switch_led", "value": True},
                    {"code": "work_mode", "value": "white"},
                    {"code": "temp_value_v2", "value": value}])
        return f"Set {_label(dev)} to {key} white."
    except Exception as e:
        return _fmt_err(e)


@registry.tool
def light_status(name: str = "") -> str:
    """Get the current state of a smart light (on/off, brightness, mode).

    Args:
        name: Which light (by name); leave empty if there's only one.
    """
    try:
        dev = _resolve(name)
    except LightLookupError as e:
        return str(e)
    try:
        resp = _get_cloud().getstatus(dev)
    except Exception as e:
        return _fmt_err(e)
    if not isinstance(resp, dict) or not resp.get("success"):
        return "Couldn't read the light's status."
    dps = {item["code"]: item["value"] for item in resp.get("result", []) if "code" in item}
    if not dps:
        return "Couldn't read the light's status."
    parts = [f"power {'on' if dps.get('switch_led') else 'off'}"]
    mode = dps.get("work_mode")
    if mode:
        parts.append(f"mode {mode}")
    bright = dps.get("bright_value_v2")
    if isinstance(bright, int):
        parts.append(f"brightness {round(bright / 10)}%")
    return f"{_label(dev)} is " + ", ".join(parts) + "."
