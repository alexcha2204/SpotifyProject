import spotipy
import time
from datetime import datetime
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException
from flask import Flask, request, url_for, session, redirect
from collections import defaultdict
import pandas as pd
import json

spotifyApp = Flask(__name__)
spotifyApp.config['SESSION_COOKIE_NAME'] = 'Release Radar Cookie'
spotifyApp.secret_key = 'SECRET_KEY'
DELAY_TIME = 2
BATCH_SIZE = 50
TOKEN_INFO = 'token_info'

@spotifyApp.route('/')
def login():
    auth_url = create_spotify_oauth().get_authorize_url()
    return redirect(auth_url)

@spotifyApp.route('/redirect')
def redirect_page():
    session.clear()
    code = request.args.get('code')
    token_info = create_spotify_oauth().get_access_token(code)
    session[TOKEN_INFO] = token_info
    return redirect(url_for('release_radar_clone', _external = True))

@spotifyApp.route('/releaseRadarClone')
def release_radar_clone():

    try:
        token_info = get_token()
    except Exception as e:
        print(f"Error obtaining Spotify token: {str(e)}")
        return redirect('/')

    sp = spotipy.Spotify(auth=token_info['access_token'])
    
    user_info = sp.current_user()
    username = user_info['id']

    artist_data = {}
    offset = 0

    while True:
        try:
            liked_songs = sp.current_user_saved_tracks(limit=BATCH_SIZE, offset=offset)['items']

            for song in liked_songs:
                local = song['track']['is_local']
                if not local:
                    get_music_data(artist_data, song)

            if len(liked_songs) < BATCH_SIZE:
                break

            offset += BATCH_SIZE

        except SpotifyException as e:
            if e.http_status == 429:
                retry_after = int(e.headers.get('Retry-After', DELAY_TIME))
                time.sleep(retry_after)
            else:
                print(f"Spotify API error getting user's saved tracks: {e}")
                break

    genres_data = get_genre_mapping(sp, artist_data)

    upload_music_data_locally(username, artist_data, genres_data)
    
    return "DATA HAS BEEN UPLOADED LOCALLY"

def get_genre_mapping(sp: spotipy.Spotify, user_data: dict):

    genres_dict = defaultdict(list)
    artist_ids = [artist['artist_id'] for artist in user_data.values()]
    artist_ids_length = len(artist_ids)

    for start in range (0, artist_ids_length, BATCH_SIZE):
       end = start + BATCH_SIZE
       chunk_of_artist_ids = artist_ids[start:end]

       artists_info = sp.artists(chunk_of_artist_ids)['artists']

       for artist_info in artists_info:
           artist_name = artist_info['name']
           artist_genres = artist_info['genres']

           for genre in artist_genres:
               genres_dict[genre].append(artist_name)

    return genres_dict

def upload_music_data_locally(username: str, artists_dict: dict, genres_dict: dict):

    artist_df = pd.DataFrame.from_dict(artists_dict, orient='index')

    artists_data_csv_filename = f"music_data_{username}.csv"
    genres_json_filename = f"genres_{username}.json"

    artist_df.to_csv(artists_data_csv_filename, index=False)

    with open(genres_json_filename, 'w') as json_file:
        json.dump(genres_dict, json_file, indent=4)     

def get_music_data(artists_data: dict, song: dict,  all_songs: dict):
    
    artists = song['track']['artists']
    date_added = datetime.fromisoformat(song['added_at'])
    song_name = song['track']['name']

    if 'album' in song['track'] and song['track']['album']:
        album_name = song['track']['album']['name']
        album_type = song['track']['album']['album_type']
    else:
        album_name = None
        album_type = None

    if album_name is None:
        print(f"Skipping song due to missing information: {song_name} by {artists}")
    else:
        for artist in artists:

            artist_name = artist['name']
            artist_id = artist['id']

            if artist_name not in artists_data:

                artists_data[artist_name] = artists_data_dictionary(artist_name, artist_id, 
                                                                        date_added, song_name, album_name, album_type,
                                                                        date_added, song_name, album_name, album_type, 
                                                                        0, 0, 0)
                
            if artist_name == artists[0]['name']:
                artists_data[artist_name]["main_songs_count"] += 1
            else:
                artists_data[artist_name]["featured_songs_count"] += 1

            artists_data[artist_name]["liked_songs_count"] += 1
            
            if date_added > artists_data[artist_name]['last_added']:
                artists_data[artist_name]['last_added'] = date_added
                artists_data[artist_name]['last_song'] = song_name
                artists_data[artist_name]['last_album'] = album_name
                artists_data[artist_name]['last_album_type'] = album_type

            if date_added < artists_data[artist_name]['first_added']:
                artists_data[artist_name]['first_added'] = date_added
                artists_data[artist_name]['first_song'] = song_name
                artists_data[artist_name]['first_album'] = album_name
                artists_data[artist_name]['first_album_type'] = album_type 


def artists_data_dictionary(artist_name: str, artist_id: str, first_added: datetime, first_song: str, 
                            first_album: str, first_album_type: str,last_added: datetime, last_song: str, 
                            last_album: str, last_album_type: str, num_songs_main: int, num_songs_feature: int, 
                            liked_songs: int):
    return {
        "artist_name": artist_name,
        "artist_id" : artist_id, 
        "first_added" : first_added, 
        "first_song": first_song,
        "first_album": first_album,
        "first_album_type": first_album_type,
        "last_added" : last_added,
        "last_song": last_song,
        "last_album": last_album,
        "last_album_type": last_album_type,
        "main_songs_count" : num_songs_main, 
        "featured_songs_count" : num_songs_feature, 
        "liked_songs_count" : liked_songs}

def get_token():

    token_info = session.get(TOKEN_INFO, None)
    if not token_info:
        redirect(url_for("login", _external=False))
    
    now = int(time.time())

    is_expired = token_info['expires_at'] - now < 60
    if is_expired:
        spotify_oauth = create_spotify_oauth()
        token_info = spotify_oauth.refresh_access_token(token_info['refresh_token'])

    with open('token.txt', 'w') as token_file:
        token_file.write(token_info['access_token'])
    
    return token_info

def code_to_be_worked_later():
     # albums_json_filename = f"albums_{username}.json"

    # with open("juice_wrld_saved.json", 'w') as json_file:
    #    json.dump(songs, json_file, indent=4)

    # with open(albums_json_filename, 'w') as json_file:
    #     json.dump(albums_dict, json_file, indent=4)
    # if artist_name not in all_songs and artist_name == match_name:
    #             all_songs[artist_name] = {"id": artist_id, 'songs': {}}

    #             album_details = {
    #                 "album_name": album_name,
    #                 "album_id": song['track']['album']['id'],
    #                 "release_date": song['track']['album']['release_date'],
    #                 'date_added': date_added.isoformat(),
    #                 'is_single': True,
    #                 "album_songs": []
    #             }

    #             all_songs[artist_name]['songs'][album_name] = album_details 
    #             all_songs[artist_name]['songs'][album_name]['album_songs'].append({
    #                 "song_name": song_name,
    #                 'song_id': song['track']['id'],
    #                 "date_added": date_added.isoformat(),
    #                 "explicit": song['track']['explicit']
    #             })

    #             if album_name != song_name:
    #                 all_songs[artist_name]['songs']['is_single'] = False

    #         if artist_name == match_name:
    #             if album_name not in all_songs[artist_name]['songs']:
    #                 all_songs[artist_name]['songs'][album_name] = {
    #                     "release_date": song['track']['album']['release_date'],
    #                     "album_songs": []
    #                 }

    #             if song['track']['album']['id'] not in all_songs[artist_name]['songs'][album_name]:
    #                 all_songs[artist_name]['songs'][album_name][song['track']['album']['id']] = {
    #                     "release_date": song['track']['album']['release_date'],
    #                     "album_songs": []
    #                 }

    #             all_songs[artist_name]['songs'][album_name][song['track']['album']['id']]['album_songs'].append({
    #                 "song_name": song_name,
    #                 'song_id': song['track']['id'],
    #                 "date_added": date_added.isoformat(),
    #                 "explicit": song['track']['explicit']
    #             })
    return None

def create_spotify_oauth():
    return SpotifyOAuth(client_id = "CLIENT_ID",
                        client_secret = "CLIENT_SECRET",
                        redirect_uri = url_for('redirect_page', _external=True),
                        scope = 'user-library-read playlist-modify-public playlist-modify-private user-read-recently-played playlist-read-private user-top-read',
                        requests_timeout=10)

if __name__ == '__main__':
    spotifyApp.run(debug=True, port=5000)
