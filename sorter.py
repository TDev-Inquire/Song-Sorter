import requests
import json
import operator
from collections import Counter
import os
import base64

spotify_api_url = "https://api.spotify.com/v1/"

def get_spotify_token():
    # Check if credentials.txt exists and if it has both Client ID and Secret
    if os.path.exists('credentials.txt'):
        with open('credentials.txt', 'r') as file:
            credentials = file.read().splitlines()
            if len(credentials) < 2:
                print("credentials.txt file should contain Client ID on the first line and Client Secret on the second line.")
                return None
            client_id, client_secret = credentials
    else:
        client_id = input('Enter your Client ID: ')
        client_secret = input('Enter your Client Secret: ')
        with open('credentials.txt', 'w') as file:
            file.write(client_id + '\n' + client_secret)

    print(f"Using client_id {client_id} and client_secret {client_secret}")

    # Spotify API endpoint
    auth_url = 'https://accounts.spotify.com/api/token'
    
    # Form the header
    client_creds = f"{client_id}:{client_secret}"
    client_creds_b64 = base64.b64encode(client_creds.encode())
    headers = {
        "Authorization": f"Basic {client_creds_b64.decode()}"
    }
    
    # Form the body
    payload = {
        'grant_type': 'client_credentials'
    }
    
    # Make a POST request to the Spotify API
    print("Requesting access token from Spotify API...")
    response = requests.post(auth_url, headers=headers, data=payload)
    
    if response.status_code != 200:
        print(f"Failed to get token with response code {response.status_code}")
        raise Exception('Failed to get token: ' + response.json())
    
    token_info = response.json()
    print(f"Received access token: {token_info['access_token']}")
    return token_info['access_token']

spotify_token = get_spotify_token()

def search_song_on_spotify(song):
    query = f"{spotify_api_url}search?q={song}&type=track"
    response = requests.get(
        query, 
        headers={
            "Content-Type": "application/json", 
            "Authorization": f"Bearer {spotify_token}"
        }
    )
    json_resp = response.json()

    if "tracks" not in json_resp or not json_resp["tracks"]["items"]:
        print(f"Could not find song: {song}")
        return None
    
    first_result = json_resp["tracks"]["items"][0]
    return first_result

def get_artist_genre(artist_id):
    query = f"{spotify_api_url}artists/{artist_id}"
    response = requests.get(
        query,
        headers={
            "Content-Type": "application/json", 
            "Authorization": f"Bearer {spotify_token}"
        }
    )
    json_resp = response.json()
    genres = json_resp["genres"]
    return genres

with open("songs.txt", "r") as file:
    songs = file.readlines()

songs = songs[:184]

all_genres = []
for song in songs:
    song_info = search_song_on_spotify(song.strip())
    if song_info is None:
        continue
    artist_id = song_info['artists'][0]['id']
    genres = get_artist_genre(artist_id)
    all_genres.extend(genres)


# calculate most common genre
common_genre = Counter(all_genres).most_common(1)[0][0]

filtered_songs = []
for song in songs:
    song_info = search_song_on_spotify(song.strip())
    artist_id = song_info['artists'][0]['id']
    genres = get_artist_genre(artist_id)
    if common_genre in genres:
        filtered_songs.append(song)

with open("songs.txt", "w") as file:
    for song in filtered_songs:
        file.write(song)

songs_sorted_by_artist = sorted(filtered_songs, key=lambda song: song.split(" - ")[0])

with open("finish.txt", "w") as file:
    for song in songs_sorted_by_artist:
        file.write(song)