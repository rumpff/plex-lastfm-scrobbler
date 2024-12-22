# Plex to Last.fm Scrobbler

This project is a Python script that integrates Plex Media Server with Last.fm, allowing you to scrobble your music plays from Plex to your Last.fm account using the "Scrobbling now" feature that is missing from official Plex LastFm integration.

## Features

- Connects to Plex Media Server
- Authenticates with Last.fm
- Updates "Now Playing" status on Last.fm when a track starts playing on Plex
- Handles play, pause, and resume events from Plex

## Requirements

- Python 3.6+
- Plex Media Server
- Last.fm account
- Plex Webhook configured to send events to this script

## Installation

1. Clone this repository:
```
git clone https://github.com/ozyz/plex-lastfm-scrobbler.git
cd plex-lastfm-scrobbler
```

2. Install the required packages:
```
pip install -r requirements.txt
```

3. Copy the `.env.example` file in the project root, rename it to `.env` and add your configuration:
```
PORT=your-port
PLEX_URL=http://your-plex-server:32400
PLEX_TOKEN=your-x-plex-token
PLEX_USER=your-plex-username # Required if server admin runs this script with their X-Plex-Token, for others can be left unset
ENABLE_SCROBBLING=true/false # On false it will only display 'Now playing' on Last.fm and it won't scrobble
LASTFM_API_KEY=your-lastfm-api-key
LASTFM_API_SECRET=your-lastfm-api-secret
```

## Usage

1. Run the script:
```python plex_lastfm_scrobbler.py```

2. The script will prompt you to authorize the application with Last.fm if it's the first time running.

3. Configure your Plex Media Server to send webhooks to `http://your-ip:your-port/webhook`

4. Play music on Plex, and it should now scrobble to Last.fm

## License

This project is licensed under the MIT License.
