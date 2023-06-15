import openai
import base64
import requests
import json
import os
import lyricsgenius
from urllib.parse import urlencode
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

def get_spotify_token(client_id, client_secret):
    """
    Given a Spotify client_id and client_secret, this function returns the Spotify token.
    """
    client_creds = f"{client_id}:{client_secret}"
    client_creds_b64 = base64.b64encode(client_creds.encode())
    token_url = "https://accounts.spotify.com/api/token"
    method = "POST"
    token_data = {"grant_type": "client_credentials"}
    token_headers = {"Authorization": f"Basic {client_creds_b64.decode()}"}
    r = requests.post(token_url, data=token_data, headers=token_headers)
    token_response_data = r.json()
    return token_response_data["access_token"]

def search_song_on_spotify(song, token):
    """
    Given a song name and a Spotify token, this function returns the song information from Spotify.
    """
    headers = {
        "Authorization": "Bearer " + token
    }
    endpoint = "https://api.spotify.com/v1/search"
    data = urlencode({"q": song, "type": "track"})
    lookup_url = f"{endpoint}?{data}"
    r = requests.get(lookup_url, headers=headers)
    return r.json()["tracks"]["items"][0] if r.json()["tracks"]["items"] else None

def get_artist_genre(artist_id, token):
    """
    Given an artist id and a Spotify token, this function returns the genres associated with the artist.
    """
    headers = {
        "Authorization": "Bearer " + token
    }
    endpoint = f"https://api.spotify.com/v1/artists/{artist_id}"
    r = requests.get(endpoint, headers=headers)
    return r.json()["genres"]

def get_song_lyrics(artist, song_title, genius_token):
    """
    Given an artist, a song title, and a Genius token, this function returns the lyrics of the song.
    """
    genius = lyricsgenius.Genius(genius_token)
    song = genius.search_song(song_title, artist)
    if song is not None:
        return song.lyrics
    else:
        return None

def predict_genre(song, lyrics, openai_key):
    """
    Given a song, its lyrics, and an OpenAI key, this function uses OpenAI GPT-3 to predict the genre of the song.
    """
    openai.api_key = openai_key
    response = openai.Completion.create(engine="text-davinci-002", prompt=f"This song has the following lyrics: {lyrics}. What genre does this song belong to?", temperature=0.5, max_tokens=60)
    return response.choices[0].text.strip()

def get_credentials():
    """
    This function returns the Spotify Client ID, Spotify Client Secret, Genius Token, and OpenAI key.
    It first checks for a file named "credentials.txt". If the file is not found, it prompts the user for these values.
    """
    if not os.path.isfile("credentials.txt"):
        with open("credentials.txt", "w") as file:
            spotify_id = input("Enter your Spotify Client ID: ")
            spotify_secret = input("Enter your Spotify Client Secret: ")
            genius_token = input("Enter your Genius Access Token: ")
            openai_key = input("Enter your OpenAI Key: ")
            file.write(f"{spotify_id}\n{spotify_secret}\n{genius_token}\n{openai_key}")
    
    with open("credentials.txt", "r") as file:
        lines = file.readlines()
        spotify_id = lines[0].strip()
        spotify_secret = lines[1].strip()
        genius_token = lines[2].strip()
        openai_key = lines[3].strip()
        
    return spotify_id, spotify_secret, genius_token, openai_key

def main():
    spotify_id, spotify_secret, genius_token, openai_key = get_credentials()

    spotify_token = get_spotify_token(spotify_id, spotify_secret)

    with open('songs.txt', 'r') as f:
        song_list = [line.strip() for line in f.readlines()][:184]

    song_list = list(set(song_list))  # Remove duplicates
    song_list.sort()  # Sort alphabetically

    song_genres = defaultdict(list)

    # Multithreading for speed
    with ThreadPoolExecutor(max_workers=20) as executor:
        for song in tqdm(song_list, desc='Processing songs', ncols=70):  # tqdm for progress bar
            future = executor.submit(process_song, song, spotify_token, genius_token, openai_key)
            song_genres.update(future.result())

    with open('songs.txt', 'w') as f:
        for genre, songs in song_genres.items():
            for song in songs:
                f.write(f"{song}\n")

def process_song(song, spotify_token, genius_token, openai_key):
    song_genre = defaultdict(list)
    print(f"Processing song: {song}")  # show function execution
    song_info = search_song_on_spotify(song, spotify_token)
    if song_info is not None:
        artist_id = song_info["artists"][0]["id"]
        genres = get_artist_genre(artist_id, spotify_token)
        if genres:
            for genre in genres:
                song_genre[genre].append(song)
        else:
            # Get the song's lyrics and use GPT-3 to predict the genre.
            artist, song_title = song.split(' - ', 1)
            song_lyrics = get_song_lyrics(artist, song_title, genius_token)
            if song_lyrics:
                if len(song_lyrics) > 2000:  # Truncate the lyrics if they are too long
                    song_lyrics = song_lyrics[:2000]
                genre_prediction = predict_genre(song, song_lyrics, openai_key)
                song_genre[genre_prediction].append(song)
    return song_genre

if __name__ == "__main__":
    main()