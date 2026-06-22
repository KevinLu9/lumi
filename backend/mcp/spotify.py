"""Spotify Web API tools — requires SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET in .env.
Run `python -m backend.mcp.spotify_auth` once to authenticate and cache the token."""

import os
from dotenv import load_dotenv

load_dotenv()

_sp = None


def _get_client():
    global _sp
    if _sp is None:
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth
        _sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=os.environ["SPOTIFY_CLIENT_ID"],
            client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
            redirect_uri=os.environ.get("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback"),
            scope=(
                "user-read-playback-state "
                "user-modify-playback-state "
                "user-read-currently-playing "
                "playlist-read-private "
                "playlist-read-collaborative"
            ),
            cache_path=os.path.join(os.path.dirname(__file__), ".spotify_cache"),
            open_browser=False,
        ))
    return _sp


def _fmt_err(e) -> str:
    msg = str(e)
    if "NO_ACTIVE_DEVICE" in msg or "404" in msg:
        return "No active Spotify device found — open Spotify on a device first"
    return f"Spotify error: {e}"


def spotify_now_playing() -> str:
    """Get the currently playing track on Spotify including artist and progress."""
    try:
        current = _get_client().current_playback()
    except Exception as e:
        return _fmt_err(e)
    if not current or not current.get("item"):
        return "Nothing is currently playing on Spotify"
    item = current["item"]
    track = item["name"]
    artists = ", ".join(a["name"] for a in item["artists"])
    album = item["album"]["name"]
    p = current.get("progress_ms", 0)
    d = item["duration_ms"]
    progress = f"{p // 60000}:{(p % 60000) // 1000:02d}"
    duration = f"{d // 60000}:{(d % 60000) // 1000:02d}"
    state = "playing" if current["is_playing"] else "paused"
    return f"'{track}' by {artists} from '{album}' — {progress}/{duration} ({state})"


def spotify_play_pause() -> str:
    """Toggle Spotify playback — pause if playing, resume if paused."""
    try:
        sp = _get_client()
        current = sp.current_playback()
        if current and current["is_playing"]:
            sp.pause_playback()
            return "Paused"
        else:
            sp.start_playback()
            return "Resumed"
    except Exception as e:
        return _fmt_err(e)


def spotify_next() -> str:
    """Skip to the next track on Spotify."""
    try:
        _get_client().next_track()
        return "Skipped to next track"
    except Exception as e:
        return _fmt_err(e)


def spotify_previous() -> str:
    """Go back to the previous track on Spotify."""
    try:
        _get_client().previous_track()
        return "Went back to previous track"
    except Exception as e:
        return _fmt_err(e)


def spotify_set_volume(volume_percent: int) -> str:
    """Set the Spotify playback volume.

    Args:
        volume_percent: Volume level from 0 (silent) to 100 (max).
    """
    try:
        vol = max(0, min(100, volume_percent))
        _get_client().volume(vol)
        return f"Volume set to {vol}%"
    except Exception as e:
        return _fmt_err(e)


def spotify_play(query: str) -> str:
    """Search Spotify and immediately play the best matching song or artist.

    Args:
        query: Song title, artist name, or 'song by artist', e.g. 'Blinding Lights' or 'The Weeknd'.
    """
    try:
        sp = _get_client()
        results = sp.search(query, limit=3, type="track,artist")
        tracks = results["tracks"]["items"]
        artists = results["artists"]["items"]

        # Prefer a track match unless the query looks like a pure artist name
        # (i.e. no track results or top artist relevance is very high).
        if tracks:
            t = tracks[0]
            sp.start_playback(uris=[t["uri"]])
            return f"Playing '{t['name']}' by {t['artists'][0]['name']}"

        if artists:
            top = sp.artist_top_tracks(artists[0]["id"])["tracks"]
            if top:
                sp.start_playback(uris=[t["uri"] for t in top[:5]])
                return f"Playing top tracks by {artists[0]['name']}"

        return f"Nothing found on Spotify for '{query}'"
    except Exception as e:
        return _fmt_err(e)


def spotify_play_playlist(name: str) -> str:
    """Find and play one of the user's Spotify playlists by name.

    Args:
        name: Full or partial playlist name, e.g. 'chill vibes' or 'workout'.
    """
    try:
        sp = _get_client()
        results = sp.current_user_playlists(limit=50)
        playlists = results["items"]
        name_lower = name.lower()
        match = next((p for p in playlists if name_lower in p["name"].lower()), None)
        if not match:
            names = ", ".join(p["name"] for p in playlists[:10])
            return f"No playlist matching '{name}'. Your playlists: {names}"
        sp.start_playback(context_uri=match["uri"])
        return f"Playing playlist '{match['name']}'"
    except Exception as e:
        return _fmt_err(e)


def spotify_queue(query: str) -> str:
    """Search Spotify and add the best matching track to the queue.

    Args:
        query: Song title or 'song by artist', e.g. 'Levitating by Dua Lipa'.
    """
    try:
        sp = _get_client()
        results = sp.search(query, limit=1, type="track")
        tracks = results["tracks"]["items"]
        if not tracks:
            return f"No track found for '{query}'"
        t = tracks[0]
        sp.add_to_queue(t["uri"])
        return f"Added '{t['name']}' by {t['artists'][0]['name']} to queue"
    except Exception as e:
        return _fmt_err(e)


def spotify_transfer_playback(device_name: str) -> str:
    """Transfer Spotify playback to a different device by name.

    Args:
        device_name: Full or partial name of the target device, e.g. 'MacBook' or 'Kitchen'.
    """
    try:
        sp = _get_client()
        devices = sp.devices()["devices"]
        if not devices:
            return "No Spotify devices found. Open Spotify on a device first."
        name_lower = device_name.lower()
        match = next((d for d in devices if name_lower in d["name"].lower()), None)
        if not match:
            names = ", ".join(d["name"] for d in devices)
            return f"No device matching '{device_name}'. Available: {names}"
        sp.transfer_playback(match["id"], force_play=True)
        return f"Playback transferred to {match['name']}"
    except Exception as e:
        return _fmt_err(e)


def spotify_list_devices() -> str:
    """List all Spotify-connected devices and which one is currently active."""
    try:
        devices = _get_client().devices()["devices"]
        if not devices:
            return "No Spotify devices found. Open Spotify on a device first."
        lines = []
        for d in devices:
            active = " (active)" if d["is_active"] else ""
            lines.append(f"{d['name']} — {d['type']}{active}")
        return ", ".join(lines)
    except Exception as e:
        return _fmt_err(e)


def spotify_list_playlists() -> str:
    """List all of the user's Spotify playlists."""
    try:
        sp = _get_client()
        results = sp.current_user_playlists(limit=50)
        playlists = results["items"]
        if not playlists:
            return "You have no playlists on Spotify."
        return ", ".join(p["name"] for p in playlists)
    except Exception as e:
        return _fmt_err(e)


TOOL_FNS: dict = {
    "spotify_now_playing": spotify_now_playing,
    "spotify_play_pause": spotify_play_pause,
    "spotify_next": spotify_next,
    "spotify_previous": spotify_previous,
    "spotify_set_volume": spotify_set_volume,
    "spotify_play": spotify_play,
    "spotify_play_playlist": spotify_play_playlist,
    "spotify_queue": spotify_queue,
    "spotify_list_playlists": spotify_list_playlists,
    "spotify_list_devices": spotify_list_devices,
    "spotify_transfer_playback": spotify_transfer_playback,
}

TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "spotify_now_playing",
            "description": "Get the currently playing track on Spotify including artist and progress.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "spotify_play_pause",
            "description": "Toggle Spotify playback — pause if playing, resume if paused.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "spotify_next",
            "description": "Skip to the next track on Spotify.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "spotify_previous",
            "description": "Go back to the previous track on Spotify.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "spotify_set_volume",
            "description": "Set the Spotify playback volume.",
            "parameters": {
                "type": "object",
                "properties": {
                    "volume_percent": {
                        "type": "integer",
                        "description": "Volume level from 0 (silent) to 100 (max).",
                    }
                },
                "required": ["volume_percent"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "spotify_play",
            "description": "Search Spotify and immediately play the best matching song or artist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Song title, artist name, or 'song by artist'.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "spotify_play_playlist",
            "description": "Find and play one of the user's Spotify playlists by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Full or partial playlist name.",
                    }
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "spotify_queue",
            "description": "Search Spotify and add the best matching track to the queue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Song title or 'song by artist'.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "spotify_list_playlists",
            "description": "List all of the user's Spotify playlists.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "spotify_list_devices",
            "description": "List all Spotify-connected devices and which one is currently active.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "spotify_transfer_playback",
            "description": "Transfer Spotify playback to a different device by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "device_name": {
                        "type": "string",
                        "description": "Full or partial name of the target device, e.g. 'MacBook' or 'Kitchen'.",
                    }
                },
                "required": ["device_name"],
            },
        },
    },
]
