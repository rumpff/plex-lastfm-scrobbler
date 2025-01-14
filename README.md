# Plex to Last.fm Scrobbler

This is a fork by miitchel and rumpff. We added to ability to actually scrobble (not only 'Now playing') to Last.fm, and for multiple users. This fork uses a YAML config instead of .env.

## Features

- Connects to Plex Media Server
- Authenticates with Last.fm
- Updates "Now Playing" status on Last.fm when a track starts playing on Plex
- Handles play, pause, and resume events from Plex
- Scrobbles to Last.fm
- Handles multiple Last.fm users
- YAML config

## Requirements

- Python 3.6+
- Plex Media Server
- Last.fm API account
- Plex Webhook configured to send events to this script

## Installation

1. Clone this repository:
```
git clone https://github.com/rumpff/plex-lastfm-scrobbler.git
cd plex-lastfm-scrobbler
```

2. Install the required packages:
```
pip install -r requirements.txt
```

3. Copy the `config.yaml.example` file in the project root, rename it to `config.yaml` and add your configuration:  
Create an API account on https://www.last.fm/api/account/create
```
webhook_port:
plex_url:
x_plex_token:
users:
  plex-username:
    lastfm_api_key: 
    lastfm_api_secret: 
    lastfm_session_key: # LEAVE EMPTY
    enable_scrobbling: true
```
You can add multiple users to the config. You need to be able to log into the other users' Last.fm account for the session key.  
Example:
```
webhook_port:
plex_url:
x_plex_token:
users:
  user1:
    lastfm_api_key: 
    lastfm_api_secret: 
    lastfm_session_key: # LEAVE EMPTY
    enable_scrobbling: true
  user2:
    lastfm_api_key: 
    lastfm_api_secret: 
    lastfm_session_key: # LEAVE EMPTY
    enable_scrobbling: true
  user3:
    ...
```


## Usage

1. Configure your Plex Media Server to send webhooks to `http://your-ip:your-port/webhook`

2. Run the script:
```python plex_lastfm_scrobbler.py```

3. User starts playback

4. The script will prompt you to authorize the application with Last.fm if it's the first time running.

5. Play music on Plex, and it should now scrobble to Last.fm

## License

This project is licensed under the MIT License.
