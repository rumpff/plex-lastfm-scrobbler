import os
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

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger('werkzeug')
log.setLevel(logging.INFO) 

# Flask app for webhook
app = Flask(__name__)

def get_lastfm_session_key(user):
    if user['user_data'].get("lastfm_session_key"):
        return user['user_data'].get("lastfm_session_key")
    
    network = pylast.LastFMNetwork(api_key=config["lastfm_api_key"], api_secret=config["lastfm_api_secret"])
    sg = pylast.SessionKeyGenerator(network)
    url = sg.get_web_auth_url()

    print(f"Please open this URL in your browser and authorize the application: {url}")
    # webbrowser.open(url)
    
    while True:
        try:
            session_key = sg.get_web_auth_session_key(url)
            config["users"][user['user_name']]["lastfm_session_key"] = session_key

            with open("config.yaml", "w") as file:
                yaml.dump(config, file, default_flow_style=False, sort_keys=False)

            return session_key
        except pylast.WSError:
            print("Waiting for authorization...")
            time.sleep(5)
    
def get_track_info(metadata):
    
    # look for musicbrainz ID
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
        'mbid': mbid,
        'timestamp': time.time()
    }

    return track_info

def update_now_playing(user, track_info):
    try:
        get_lastfm_user(user).update_now_playing(
            artist=track_info['artist'],
            title=track_info['title'],
            album=track_info['album'],
            album_artist=track_info['album_artist'],
            track_number=track_info['track_number'],
            mbid=track_info['mbid']
        )
        log.info(f"{user['user_name']} is now playing: {track_info['artist']} - {track_info['title']} (on {track_info['album_artist']} - {track_info['album']})")    
        return
        
    except pylast.WSError as e:
        log.error(f"Error updating now playing: {e}")
        return

def scrobble(user, track_info):
    if user['user_data']["enable_scrobbling"]:
        try:
            get_lastfm_user(user).scrobble(
                        artist=track_info['artist'],
                        title=track_info['title'],
                        album=track_info['album'],
                        album_artist=track_info['album_artist'],
                        track_number=track_info['track_number'],
                        mbid=track_info['mbid'],
                        timestamp=track_info['timestamp']
                    )
            log.info(f"{user['user_name'] } scrobbled: {track_info['artist']} - {track_info['title']} (on {track_info['album_artist']} - {track_info['album']})")
            return
        except pylast.WSError as e:
            log.error(f"Error scrobbling: {e}")
            return
        
    else:
        log.debug("user['user_name']'s scrobble ignored")
        return

def process_webhook(webhook_data):

    user = {}
    user['user_name'] = webhook_data.get('Account', {}).get('title')
    user['user_data'] = users.get(user['user_name'])

    if not user['user_data']:
        log.debug(f"Plex user '{user['user_name']}' not found in config")
        return
    
    # uncomment for debugging:
    #print("Parsed inner data:")
    #print(json.dumps(data, indent=2))
    
    metadata = webhook_data.get('Metadata', {})

    track_info = get_track_info(metadata)

    # print(track_info)

    if metadata.get('type') == 'track':
        event = webhook_data.get('event')

        if event in ['media.play','playback.started', 'media.resume']:
            return update_now_playing(user, track_info) 

        elif event == 'media.scrobble':
            return scrobble(user, track_info)

        else:
            log.debug(f"event {event} ignored")
            return
        

@app.route('/webhook', methods=['POST'])
def webhook():
    log.debug("in webhook")
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
            return jsonify({"status": "error", "message": "Invalid payload JSON", "log_level": "ERROR"}), 400

    else:
        data = outer_data

    process_webhook(data)
    return jsonify({"status": "webhook success", "log_level": "DEBUG"}), 200


def get_lastfm_user(user):
    network = pylast.LastFMNetwork(
        api_key=config["lastfm_api_key"],
        api_secret=config["lastfm_api_secret"],
        session_key=get_lastfm_session_key(user)
    )

    return network

def main():
    global network

    print("Script started. Waiting for Plex webhooks...")
    app.run(host='0.0.0.0', port=config["webhook_port"])

if __name__ == "__main__":
    main()
