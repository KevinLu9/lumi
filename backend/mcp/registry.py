"""Unified tool registry — merges base tools and any optional integrations."""

import os
from .tools import (
    TOOL_FNS as _base_fns,
    TOOL_SCHEMAS as _base_schemas,
    get_time, get_weather, calculate, set_timer, reset_chat,
)
from .browser import (
    TOOL_FNS as _br_fns,
    TOOL_SCHEMAS as _br_schemas,
    browser_navigate, browser_read_page, browser_click,
)
from .keyboard import (
    TOOL_FNS as _kb_fns,
    TOOL_SCHEMAS as _kb_schemas,
    type_text,
)


TOOL_FNS: dict = dict(_base_fns)
TOOL_FNS.update(_br_fns)
TOOL_FNS.update(_kb_fns)
TOOL_SCHEMAS: list[dict] = list(_base_schemas) + list(_br_schemas) + list(_kb_schemas)
# Python callables passed to Gemini (it generates schemas from docstrings + type hints).
TOOL_CALLABLES: list = [
    get_time, get_weather, calculate, set_timer, reset_chat,
    browser_navigate, browser_read_page, browser_click,
    type_text,
]

if os.environ.get("SPOTIFY_CLIENT_ID"):
    from .spotify import (
        TOOL_FNS as _sp_fns,
        TOOL_SCHEMAS as _sp_schemas,
        spotify_now_playing, spotify_play_pause, spotify_next, spotify_previous,
        spotify_set_volume, spotify_play, spotify_play_playlist, spotify_queue,
        spotify_list_playlists, spotify_list_devices, spotify_transfer_playback,
    )
    TOOL_FNS.update(_sp_fns)
    TOOL_SCHEMAS.extend(_sp_schemas)
    TOOL_CALLABLES.extend([
        spotify_now_playing, spotify_play_pause, spotify_next, spotify_previous,
        spotify_set_volume, spotify_play, spotify_play_playlist, spotify_queue,
        spotify_list_playlists, spotify_list_devices, spotify_transfer_playback,
    ])

if os.environ.get("TUYA_DEVICE_ID"):
    from .tuya import (
        TOOL_FNS as _tuya_fns,
        TOOL_SCHEMAS as _tuya_schemas,
        light_list, light_set_power, light_set_all_power, light_set_brightness,
        light_set_color, light_set_white, light_status,
    )
    TOOL_FNS.update(_tuya_fns)
    TOOL_SCHEMAS.extend(_tuya_schemas)
    TOOL_CALLABLES.extend([
        light_list, light_set_power, light_set_all_power, light_set_brightness,
        light_set_color, light_set_white, light_status,
    ])
