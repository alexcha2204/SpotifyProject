import spotipy
import time
from datetime import datetime, timezone
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException
from flask import Flask, request, url_for, session, redirect
from azure.storage.blob import BlobServiceClient
import pandas as pd

spotifyApp = Flask(__name__)
spotifyApp.config['SESSION_COOKIE_NAME'] = 'Release Radar Cookie'
spotifyApp.secret_key = 'ehfuhrv&@98#8b976fvt$52'
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
        print(f"Error: {str(e)}")
        return redirect('/')

    sp = spotipy.Spotify(auth=token_info['access_token'])
    artists_details = {}
    delay_time = 2

    batch_size = 50
    offset = 0
    while True:
        try:
            response = sp.current_user_saved_tracks(limit=batch_size, offset=offset)
            liked_songs = response['items']

            for song in liked_songs:
                local = song['track']['is_local']
                if not local:
                    get_song_data(artists_details,song)

            if len(liked_songs) < batch_size:
                break

            offset += batch_size

        except SpotifyException as e:
            if e.http_status == 429:
                retry_after = int(e.headers.get('Retry-After', delay_time))
                time.sleep(retry_after)
            else:
                print(f"Spotify API error: {e}")
                break

    data = pd.DataFrame.from_dict(artists_details, orient='index')
   
    connection_string = "DefaultEndpointsProtocol=https;AccountName=releaseradarclone;AccountKey=7+aZMfOEpMigNFdZU5BLGM9BSZqhnJLGO7WOkctR2tMS+izjgplPko6O5BTU0q1+1Ih4C49Z5EfB+AStWRg0/Q==;EndpointSuffix=core.windows.net"  # or sas_token
    container_name = "music-data"

    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)

    if not container_client.exists():
        container_client.create_container()

    data.to_csv('music_data.csv', index=False)
    with open('music_data.csv', "rb") as data:
        blob_client = container_client.get_blob_client("music_data.csv")
        blob_client.upload_blob(data, overwrite=True)

    return "IT WORKS"

def artist_details_dictionary(artist_name: str, artist_id: str, first_added: datetime, first_song: str, first_album: str, first_album_type: str,
                              last_added: datetime, last_song: str, last_album: str, last_album_type: str, num_songs_main: int, num_songs_feature: int, liked_songs: int):
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
        "number_songs_main_artist" : num_songs_main, 
        "number_songs_featured_on" : num_songs_feature, 
        "amount_of_liked_songs" : liked_songs}

def get_song_data(artists_details: dict, song: dict):

    artist_list = song['track']['artists']
    date_added = song['added_at']
    song_name = song['track']['name']
    album_name = song['track']['album']['name']
    album_type = song['track']['album']['album_type']
    date_added = datetime.fromisoformat(date_added)

    for artist in artist_list:
        artist_name = artist['name']
        artist_id = artist['id']
        
        if artist_name not in artists_details:
            artists_details[artist_name] = artist_details_dictionary(artist_name, artist_id, 
                                                                     date_added, song_name, album_name, album_type,
                                                                     date_added, song_name, album_name, album_type, 0,0,0)
        
        if artist_name == artist_list[0]['name']:
            artists_details[artist_name]["number_songs_main_artist"] += 1
        else:
            artists_details[artist_name]["number_songs_featured_on"] += 1

        artists_details[artist_name]['amount_of_liked_songs'] += 1
        
        if date_added > artists_details[artist_name]['last_added']:
            artists_details[artist_name]['last_added'] = date_added
            artists_details[artist_name]['last_song'] = song_name
            artists_details[artist_name]['last_album'] = album_name
            artists_details[artist_name]['last_album_type'] = album_type

        if date_added < artists_details[artist_name]['first_added']:
            artists_details[artist_name]['first_added'] = date_added
            artists_details[artist_name]['first_song'] = song_name
            artists_details[artist_name]['first_album'] = album_name
            artists_details[artist_name]['first_album_type'] = album_type

    pass 

def get_token():
    token_info = session.get(TOKEN_INFO, None)
    if not token_info:
        redirect(url_for("login", _external=False))
    
    now = int(time.time())

    is_expired = token_info['expires_at'] - now < 60
    if is_expired:
        spotify_oauth = create_spotify_oauth()
        token_info = spotify_oauth.refresh_access_token(token_info['refresh_token'])
    
    return token_info

def create_spotify_oauth():
    return SpotifyOAuth(client_id = "c453297c655645b9a6deac19b000ac81",
                        client_secret = "370a6b35d2c8443eb2dbe324af8d1291",
                        redirect_uri = url_for('redirect_page', _external=True),
                        scope = 'user-library-read playlist-modify-public playlist-modify-private user-read-recently-played playlist-read-private user-top-read')

if __name__ == '__main__':
    spotifyApp.run(debug=True, port=5000)
