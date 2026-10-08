import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

def test_playlists():
    scope = "user-modify-playback-state user-read-playback-state playlist-read-private playlist-read-collaborative user-library-read"
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
    
    try:
        playlists = sp.current_user_playlists()
        print("Your personal playlists:")
        while playlists:
            for i, playlist in enumerate(playlists['items']):
                print(f"- {playlist['name']} (URI: {playlist['uri']})")
            if playlists['next']:
                playlists = sp.next(playlists)
            else:
                break
    except Exception as e:
        print("Error fetching playlists:", e)

if __name__ == "__main__":
    test_playlists()
