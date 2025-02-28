# Google Drive Integration

## Setup

1. Enable Google Drive API
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Navigate to APIs & Services > Library
   - Search for and enable "Google Drive API"

2. Generate Credentials
   - Go to APIs & Services > Credentials
   - Click "Create Credentials" > "OAuth 2.0 Client ID"
   - Select "Desktop Application"
   - Download the credentials file as `credentials.json`
   - Place it in your project root directory

3. Configure Environment Variables
   No environment variables needed, but ensure `credentials.json` is in your project root.

### Basic Setup
```python
from src.tools.google_drive import authenticate_google_drive, search_files, upload_file, download_file

# Initialize Google Drive service
service = authenticate_google_drive()

# Search for files
results = search_files(service, "name contains 'report'")

# Upload a file
file_id = upload_file(service, 
    file_path="path/to/file.pdf",
    mime_type="application/pdf"
)

# Download a file
download_file(service,
    file_id="your_file_id",
    destination="path/to/save/file.pdf"
)
```

## Features
- OAuth2 authentication flow
- File search with custom queries
- File upload with MIME type support
- File download with progress tracking
- Token persistence for future sessions
- Automatic token refresh
- Error handling and logging

## TODOs for Future Enhancements:
- Add support for folder operations
- Implement file sharing functionality
- Add batch upload/download support
- Add support for editing Google Sheets and Docs.
- Implement real-time notifications for file updates using Google Drive API webhooks.
- Add support for Google Sheets/Docs creation
- Add support for Team Drives
- Implement file change tracking
- Handle advanced file sharing and permission settings.

## Reference
For implementation details, see: `src/tools/google_drive.py`

The implementation uses the official Google Drive API v3. For more information, refer to:
- [Google Drive API Documentation](https://developers.google.com/drive/api/v3/about-sdk)
- [Google Auth Library for Python](https://github.com/googleapis/google-auth-library-python)
