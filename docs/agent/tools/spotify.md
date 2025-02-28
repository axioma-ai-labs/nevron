# Spotify Integration

## Setup

1. Create Spotify Developer Account
   - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   - Log in with your Spotify account or create one
   - Click "Create an App"
   - Fill in the app name and description

2. Generate API Credentials
   - From your app's dashboard, click "Settings"
   - Note your Client ID and Client Secret
   - Add your redirect URI (if using remote server, can be chosen default)
   - Set app permissions under "Scopes"

3. Configure Environment Variables
   Add these to your `.env` file:
   ```bash
   SPOTIFY_CLIENT_ID=your_client_id_here
   SPOTIFY_CLIENT_SECRET=your_client_secret_here
   ```

### Basic Setup
```python
from src.tools.spotify import SpotifyTool

# Initialize Spotify client
spotify = SpotifyTool()

# Authenticate and get access token
access_token = await spotify.authenticate()

# Search for songs
songs = await spotify.search_song(
    access_token=access_token,
    query="Never Gonna Give You Up",
    limit=1
)

# Get user playlists
playlists = await spotify.get_user_playlists(
    access_token=access_token
)

# Control playback
await spotify.control_playback(
    access_token=access_token,
    action="play"  # or "pause", "skip"
)
```

## Features
- Client Credentials OAuth2 authentication
- Search for songs with customizable result limits
- Retrieve user playlists and details
- Control music playback (play, pause, skip)
- Error handling with custom SpotifyError class
- Async/await support for better performance
- Secure API communication with proper authentication

## TODOs for Future Enhancements:
- Add support for real-time listening session tracking
- Implement (collaborative) playlist creation and management
- Add track analysis and audio features
- Support for podcast playback
- Implement device management: handle multi-device playback scenarios
- Implement recommendation engine


## Reference
For implementation details, see: `src/tools/spotify.py`

The implementation uses the official Spotify Web API. For more information, refer to:
- [Spotify Web API Documentation](https://developer.spotify.com/documentation/web-api)
- [Spotify Authorization Guide](https://developer.spotify.com/documentation/general/guides/authorization)
