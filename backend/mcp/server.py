"""Standalone FastMCP server — run with: python -m backend.mcp.server (from repo root)
Also connectable from Claude Desktop or any MCP client via stdio."""

import os
from fastmcp import FastMCP
from . import tools as _tools
from . import browser as _browser
from . import keyboard as _keyboard

mcp = FastMCP("lumi-tools")


@mcp.tool()
def get_time() -> str:
    """Get the current date and time."""
    return _tools.get_time()


@mcp.tool()
def get_weather(location: str) -> str:
    """Get the current weather for a city or location.

    Args:
        location: City name or location, e.g. 'Sydney' or 'New York'.
    """
    return _tools.get_weather(location)


@mcp.tool()
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression and return the result.

    Args:
        expression: A math expression such as '2 + 2', 'sqrt(16)', or 'sin(pi / 2)'.
    """
    return _tools.calculate(expression)


@mcp.tool()
def set_timer(seconds: int, label: str = "Timer") -> str:
    """Set a countdown timer that will announce when it finishes.

    Args:
        seconds: How many seconds to wait before the timer fires.
        label: A short name for the timer, e.g. 'pasta' or 'meeting'.
    """
    return _tools.set_timer(seconds, label)


@mcp.tool()
def open_url(url: str) -> str:
    """Open a URL in the user's default web browser.

    Args:
        url: Full URL to open, e.g. 'https://youtube.com'.
    """
    return _browser.open_url(url)


@mcp.tool()
def search_web(query: str) -> str:
    """Search Google for a query and open the results in the browser.

    Args:
        query: Search terms, e.g. 'Python tutorials' or 'weather Sydney'.
    """
    return _browser.search_web(query)


@mcp.tool()
def type_text(text: str) -> str:
    """Type text into wherever the cursor currently is — the focused app or text field.

    Args:
        text: The text to insert at the current cursor location.
    """
    return _keyboard.type_text(text)


if os.environ.get("SPOTIFY_CLIENT_ID"):
    from . import spotify as _sp

    @mcp.tool()
    def spotify_now_playing() -> str:
        """Get the currently playing track on Spotify including artist and progress."""
        return _sp.spotify_now_playing()

    @mcp.tool()
    def spotify_play_pause() -> str:
        """Toggle Spotify playback — pause if playing, resume if paused."""
        return _sp.spotify_play_pause()

    @mcp.tool()
    def spotify_next() -> str:
        """Skip to the next track on Spotify."""
        return _sp.spotify_next()

    @mcp.tool()
    def spotify_previous() -> str:
        """Go back to the previous track on Spotify."""
        return _sp.spotify_previous()

    @mcp.tool()
    def spotify_set_volume(volume_percent: int) -> str:
        """Set the Spotify playback volume.

        Args:
            volume_percent: Volume level from 0 (silent) to 100 (max).
        """
        return _sp.spotify_set_volume(volume_percent)

    @mcp.tool()
    def spotify_play(query: str) -> str:
        """Search Spotify and immediately play the best matching song or artist.

        Args:
            query: Song title, artist name, or 'song by artist'.
        """
        return _sp.spotify_play(query)

    @mcp.tool()
    def spotify_play_playlist(name: str) -> str:
        """Find and play one of the user's Spotify playlists by name.

        Args:
            name: Full or partial playlist name.
        """
        return _sp.spotify_play_playlist(name)

    @mcp.tool()
    def spotify_queue(query: str) -> str:
        """Search Spotify and add the best matching track to the queue.

        Args:
            query: Song title or 'song by artist'.
        """
        return _sp.spotify_queue(query)

    @mcp.tool()
    def spotify_list_playlists() -> str:
        """List all of the user's Spotify playlists."""
        return _sp.spotify_list_playlists()

    @mcp.tool()
    def spotify_list_devices() -> str:
        """List all Spotify-connected devices and which one is currently active."""
        return _sp.spotify_list_devices()

    @mcp.tool()
    def spotify_transfer_playback(device_name: str) -> str:
        """Transfer Spotify playback to a different device by name.

        Args:
            device_name: Full or partial name of the target device.
        """
        return _sp.spotify_transfer_playback(device_name)


if __name__ == "__main__":
    mcp.run()
