# Lens Protocol Integration

## Setup

1. Enable Lens Protocol API Access
   - Go to [Lens Protocol Developer Portal](https://docs.lens.xyz/docs/developer-quickstart)
   - Create a developer account
   - Navigate to API Keys section

2. Generate API Key
   - In the Developer Portal, create a new API key
   - Copy the generated API key
   - (Optional) Set API key restrictions and rate limits

3. Configure Environment Variables
   Add these to your `.env` file:
   ```bash
   LENS_API_KEY=your_api_key_here
   LENS_PROFILE_ID=your_profile_id
   ```

### Basic Setup
```python
from src.tools.lens_protocol import LensProtocolTool

# Initialize Lens Protocol client
lens = LensProtocolTool()

# Connect to Lens Protocol
auth_credentials = {
    'api_key': 'your_api_key_here'
}
lens.initialize_connection(auth_credentials)

# Get profile information
profile = lens.get_profile("lens.dev")

# Fetch recent content
publications = lens.fetch_content({
    'limit': 5,
    'sort': 'DESC'
})

# Publish content
result = lens.publish_content(
    profile_id="your_profile_id",
    content="Hello Lens Protocol!"
)
```

## Features
- Profile information retrieval and management
- Content publication to the Lens network
- Content exploration and fetching with custom parameters
- Access to social metrics (followers, following, reactions)
- Publication statistics (comments, mirrors, reactions)
- GraphQL-based API integration
- Error handling and logging

## TODOs for Future Enhancements:
- Add support for authentication and profile management
- Implement follow/unfollow functionality
- Add comment creation and management
- Support for mirroring content
- Implement content moderation features
- Add support for media attachments
- Implement notification handling
- Add support for collecting publications
- Implement profile search functionality
- Add support for encrypted direct messaging

## Reference
For implementation details, see: `src/tools/lens_protocol.py`

The implementation uses the Lens Protocol API v2. For more information, refer to:
- [Lens Protocol Documentation](https://docs.lens.xyz/)
- [Lens Protocol API Reference](https://docs.lens.xyz/docs/api-basics)
- [GraphQL Schema Documentation](https://docs.lens.xyz/docs/authentication-quickstart)