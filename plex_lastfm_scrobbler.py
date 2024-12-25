import os
from dotenv import load_dotenv, set_key
from plexapi.server import PlexServer
import pylast
import webbrowser
import time
import json
from flask import Flask, request, jsonify
import logging
import yaml

with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

users = config["users"]

# log = logging.getLogger('werkzeug')
# log.setLevel(logging.ERROR)

# Flask app for webhook
app = Flask(__name__)

def get_lastfm_session_key(user, username):
    if user.get("lastfm_session_key"):
        return user.get("lastfm_session_key")
    
    network = pylast.LastFMNetwork(api_key=user["lastfm_api_key"], api_secret=user["lastfm_api_secret"])
    sg = pylast.SessionKeyGenerator(network)
    url = sg.get_web_auth_url()

    print(f"Please open this URL in your browser and authorize the application: {url}")
    webbrowser.open(url)
    
    while True:
        try:
            session_key = sg.get_web_auth_session_key(url)
            config["users"][username]["lastfm_session_key"] = session_key

            with open("config.yaml", "w") as file:
                yaml.dump(config, file, default_flow_style=False, sort_keys=False)

            return session_key
        except pylast.WSError:
            print("Waiting for authorization...")
            time.sleep(5)
    

@app.route('/webhook', methods=['POST'])
def webhook():
    print("in webhook")
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

    username = data.get('Account', {}).get('title')
    user = users.get(username)

    if not user:
        print("test")
        return jsonify({"status": "ignored"}), 200
    
    # uncomment for debugging:
    #print("Parsed inner data:")
    #print(json.dumps(data, indent=2))
    
    metadata = data.get('Metadata', {})

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

    print(track_info)

    if metadata.get('type') == 'track':
        event = data.get('event')

        if event in ['media.play','playback.started', 'media.resume']:
                try:
                    get_lastfm_user(user, username).update_now_playing(
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
            if user["enable_scrobbling"]:
                    track_info['timestamp'] = time.time()
                    get_lastfm_user(user, username).scrobble(
                                artist=track_info['artist'],
                                title=track_info['title'],
                                album=track_info['album'],
                                album_artist=track_info['album_artist'],
                                track_number=track_info['track_number'],
                                mbid=track_info['mbid'],
                                timestamp=track_info['timestamp']
                            )
                    print(f"{username} scrobbled: {track_info['artist']} - {track_info['title']} (on {track_info['album_artist']} - {track_info['album']})")
        #else:
            #print(f"Received event: {event}")
        
    return jsonify({"status": "success"}), 200

def get_lastfm_user(user, username):
    network = pylast.LastFMNetwork(
        api_key=user["lastfm_api_key"],
        api_secret=user["lastfm_api_secret"],
        session_key=get_lastfm_session_key(user, username)
    )

    return network

def main():
    global network

    print("Script started. Waiting for Plex webhooks...")
    app.run(host='0.0.0.0', port=config["webhook_port"])

if __name__ == "__main__":
    main()
