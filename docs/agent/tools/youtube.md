# YouTube Integration

## Setup

1. Enable YouTube Data API
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Navigate to APIs & Services > Library
   - Search for and enable "YouTube Data API v3"

2. Generate API Key
   - Go to APIs & Services > Credentials
   - Click "Create Credentials" > "API key"
   - Copy the generated API key
   - (Optional) Restrict the API key to YouTube Data API v3 only

3. Configure Environment Variables
   Add these to your `.env` file:
   ```bash
   YOUTUBE_API_KEY=your_api_key_here
   YOUTUBE_CHANNEL_ID=your_channel_id
   ```

### Basic Setup
```python
from src.tools.youtube import YouTubeClient

# Initialize YouTube client
youtube = YouTubeClient()

# Search for videos
results = youtube.search_videos(
    query="Python programming",
    max_results=5
)

# Get video details
video_details = youtube.get_video_details(
    video_id="video_id_here"
)
```

## Features
- Search for videos with custom queries and filters
- Retrieve detailed video information (title, description, statistics)
- Access video comments and engagement metrics
- Get channel statistics and details
- Fetch playlist information
- Efficient caching of API client

## TODOs for Future Enhancements:
- Add support for video uploads and management
- Implement live streaming capabilities
- Add caption/subtitle handling
- Support for video analytics and reporting
- Implement playlist creation and management
- Add support for channel management
- Implement comment moderation features
- Add support for video categories and tags

## Reference
For implementation details, see: `src/tools/youtube.py`

The implementation uses the official YouTube Data API v3. For more information, refer to:
- [YouTube Data API Documentation](https://developers.google.com/youtube/v3/docs)
- [Google API Client Library for Python](https://github.com/googleapis/google-api-python-client)