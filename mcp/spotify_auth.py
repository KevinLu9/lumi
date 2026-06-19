"""Run once to authenticate with Spotify and cache the token.
Usage (from server-python/):  python -m mcp.spotify_auth
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

required = ["SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET"]
missing = [k for k in required if not os.environ.get(k)]
if missing:
    print(f"Error: missing env vars: {', '.join(missing)}")
    print("Add them to server-python/.env and re-run.")
    sys.exit(1)

import spotipy
from spotipy.oauth2 import SpotifyOAuth

cache_path = os.path.join(os.path.dirname(__file__), ".spotify_cache")

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
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
    cache_path=cache_path,
    open_browser=True,
))

user = sp.current_user()
print(f"\nAuthenticated as: {user['display_name']} ({user['id']})")
print(f"Token cached at: {cache_path}")
print("You can now start the voice assistant.")
