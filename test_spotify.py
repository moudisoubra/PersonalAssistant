import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope="user-read-playback-state"))

# Test 1: Literal search
results1 = sp.search(q="Creep by Radiohead", type='track', limit=1)
if results1['tracks']['items']:
    print(f"Literal search found: {results1['tracks']['items'][0]['name']} by {results1['tracks']['items'][0]['artists'][0]['name']}")

# Test 2: Advanced search
results2 = sp.search(q="track:Creep artist:Radiohead", type='track', limit=1)
if results2['tracks']['items']:
    print(f"Advanced search found: {results2['tracks']['items'][0]['name']} by {results2['tracks']['items'][0]['artists'][0]['name']}")
