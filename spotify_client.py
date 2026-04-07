import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

SCOPES = "user-top-read user-read-currently-playing user-read-playback-state"


def get_spotify_oauth():
    return SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
        scope=SCOPES,
        cache_path=".spotify_cache",
        open_browser=False,
    )


def get_spotify_client():
    return spotipy.Spotify(auth_manager=get_spotify_oauth())


def get_top_tracks(sp, time_range="medium_term", limit=50):
    results = sp.current_user_top_tracks(limit=limit, time_range=time_range)
    return [{
        "id": item.get("id"),
        "name": item.get("name", "Unknown"),
        "artist": item["artists"][0]["name"] if item.get("artists") else "Unknown",
        "artist_id": item["artists"][0]["id"] if item.get("artists") else None,
        "album": item.get("album", {}).get("name", "Unknown"),
        "image": item["album"]["images"][1]["url"] if item.get("album", {}).get("images") and len(item["album"]["images"]) > 1 else None,
        "popularity": item.get("popularity", 0),
        "duration_ms": item.get("duration_ms", 0),
        "preview_url": item.get("preview_url"),
    } for item in results["items"]]


def get_top_artists(sp, time_range="medium_term", limit=50):
    results = sp.current_user_top_artists(limit=limit, time_range=time_range)
    return [{
        "id": item.get("id"),
        "name": item.get("name", "Unknown"),
        "genres": item.get("genres", []),
        "popularity": item.get("popularity", 0),
        "followers": item.get("followers", {}).get("total", 0),
        "image": item["images"][1]["url"] if item.get("images") and len(item["images"]) > 1 else None,
    } for item in results["items"]]


def get_audio_features(sp, track_ids):
    features = []
    for i in range(0, len(track_ids), 100):
        batch = sp.audio_features(track_ids[i:i + 100])
        features.extend([f for f in batch if f])
    return features


def get_currently_playing(sp):
    try:
        result = sp.current_playback()
        if result and result.get("item"):
            item = result["item"]
            return {
                "name": item.get("name", "Unknown"),
                "artist": item["artists"][0]["name"] if item.get("artists") else "Unknown",
                "album": item.get("album", {}).get("name", "Unknown"),
                "image": item["album"]["images"][0]["url"] if item.get("album", {}).get("images") else None,
                "progress_ms": result.get("progress_ms", 0),
                "duration_ms": item.get("duration_ms", 0),
                "is_playing": result.get("is_playing", False),
            }
    except Exception:
        pass
    return None


def get_genres_from_artists(artists):
    genre_counts = {}
    for artist in artists:
        for genre in artist.get("genres", []):
            genre_counts[genre] = genre_counts.get(genre, 0) + 1
    return dict(sorted(genre_counts.items(), key=lambda x: x[1], reverse=True))