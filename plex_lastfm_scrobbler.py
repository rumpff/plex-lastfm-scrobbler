import os
from dotenv import load_dotenv, set_key
from plexapi.server import PlexServer
import pylast
import webbrowser
import time
import json
from flask import Flask, request, jsonify
import logging

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Load environment variables
load_dotenv()

# Script configuration
PORT = os.getenv('PORT')

# Plex configuration
PLEX_URL = os.getenv('PLEX_URL')
PLEX_TOKEN = os.getenv('PLEX_TOKEN')
PLEX_USER = os.getenv('PLEX_USER') or ''
ENABLE_SCROBBLING = os.getenv('ENABLE_SCROBBLING', 'false').strip().lower() == 'true'

# Last.fm configuration
LASTFM_API_KEY = os.getenv('LASTFM_API_KEY')
LASTFM_API_SECRET = os.getenv('LASTFM_API_SECRET')
LASTFM_SESSION_KEY = os.getenv('LASTFM_SESSION_KEY')

# Flask app for webhook
app = Flask(__name__)


def load_session_key():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, 'r') as f:
            data = json.load(f)
            return data.get('session_key')
    return None


def save_session_key(session_key):
    with open(SESSION_FILE, 'w') as f:
        json.dump({'session_key': session_key}, f)


def get_lastfm_session_key():
    if LASTFM_SESSION_KEY:
        return LASTFM_SESSION_KEY
    
    network = pylast.LastFMNetwork(api_key=LASTFM_API_KEY, api_secret=LASTFM_API_SECRET)
    sg = pylast.SessionKeyGenerator(network)
    url = sg.get_web_auth_url()

    print(f"Please open this URL in your browser and authorize the application: {url}")
    webbrowser.open(url)
    
    while True:
        try:
            session_key = sg.get_web_auth_session_key(url)
            set_key('.env', 'LASTFM_SESSION_KEY', session_key)
            return session_key
        except pylast.WSError:
            print("Waiting for authorization...")
            time.sleep(5)
    

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('Content-Type') == 'application/json':
        outer_data = request.json
    else:
        outer_data = request.form.to_dict()
    
    # Parse the nested JSON payload
    if 'payload' in outer_data:
        try:
            data = json.loads(outer_data['payload'])
        except json.JSONDecodeError:
            print("Failed to parse payload JSON")
            return jsonify({"status": "error", "message": "Invalid payload JSON"}), 400
    else:
        data = outer_data

    event = data.get('event')
    username = data.get('Account', {}).get('title')

    if PLEX_USER != '' and username != PLEX_USER:
        return jsonify({"status": "ignored"}), 200
    
    # uncomment for debugging:
    #print("Parsed inner data:")
    #print(json.dumps(data, indent=2))
    
    metadata = data.get('Metadata', {})
    guid = metadata.get('Guid', {})

    if 'Guid' in metadata:
        mbid = metadata['Guid'][0]['id'][7:]
    else:
        mbid = ""
    
    track_info = {
        'title': metadata.get('title'),
        'artist': metadata.get('originalTitle') or metadata.get('grandparentTitle'),
        'album': metadata.get('parentTitle'),
        'album_artist': metadata.get('grandparentTitle'),
        'track_number': metadata.get('index'),
        'mbid': mbid
    }

    if event in ['media.play','playback.started', 'media.resume']:
        
        if metadata.get('type') == 'track':
            try:
                network.update_now_playing(
                    artist=track_info['artist'],
                    title=track_info['title'],
                    album=track_info['album'],
                    album_artist=track_info['album_artist'],
                    track_number=track_info['track_number'],
                    mbid=track_info['mbid']
                )
                print(f"{username} is now playing: {track_info['artist']} - {track_info['title']} (on {track_info['album_artist']} - {track_info['album']})")
                
            except pylast.WSError as e:
                print(f"Error updating now playing: {e}")
    elif event == 'media.pause':
        # For pause events, we don't update Last.fm
        # Last.fm automatically clears now playing after a while
        print("Playback paused")
    elif event == 'media.scrobble':
        if ENABLE_SCROBBLING:
            track_info['timestamp'] = time.time()
            network.scrobble(
                        artist=track_info['artist'],
                        title=track_info['title'],
                        album=track_info['album'],
                        album_artist=track_info['album_artist'],
                        track_number=track_info['track_number'],
                        mbid=track_info['mbid'],
                        timestamp=track_info['timestamp']
                    )
            print(f"{username} scrobbled: {track_info['artist']} - {track_info['title']} (on {track_info['album_artist']} - {track_info['album']})")
    else:
        print(f"Received event: {event}")
    
    return jsonify({"status": "success"}), 200


def main():
    global network
    
    # Connect to Last.fm
    session_key = get_lastfm_session_key()
    network = pylast.LastFMNetwork(
        api_key=LASTFM_API_KEY,
        api_secret=LASTFM_API_SECRET,
        session_key=session_key
    )

    print("Script started. Waiting for Plex webhooks...")
    app.run(host='0.0.0.0', port=PORT)

if __name__ == "__main__":
    main()
