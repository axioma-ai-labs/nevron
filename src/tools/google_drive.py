import os
from typing import Dict, List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload


SCOPES = ["https://www.googleapis.com/auth/drive"]


class GoogleDriveTool:
    """Google Drive integration tool for handling file operations.
    Execution Flow:
    1. Check if credentials.json exists
    2. Create token.json if it doesn't exist
    3. Use or refresh the token as needed
    4. Return authenticated service
    """

    def __init__(self):
        """Initialize the Google Drive tool with authentication."""
        self.service = self._authenticate()

    def _authenticate(self):
        """Authenticate and return the Google Drive service.

        Raises:
            FileNotFoundError: If credentials.json is not found
        """
        if not os.path.exists("credentials.json"):
            raise FileNotFoundError(
                "Credentials file not found. Please download it from Google Cloud Console."
            )

        creds = None
        if os.path.exists("token.json") and os.path.getsize("token.json") > 0:
            try:
                creds = Credentials.from_authorized_user_file("token.json", SCOPES)
            except Exception as e:
                print(f"Error reading token.json: {e}")
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("Refreshing expired token...")
                creds.refresh(Request())
            else:
                print("Getting new token from credentials.json...")
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)
                print("Successfully obtained new token.")

            with open("token.json", "w") as token:
                token.write(creds.to_json())
            print("Token saved successfully.")

        print("Building Google Drive service...")
        return build("drive", "v3", credentials=creds)

    def search_files(self, query: str) -> List[Dict]:
        """Search for files in Google Drive.

        Args:
            query: Search query

        Returns:
            List of file dictionaries with id and name
        """
        results = self.service.files().list(q=query, fields="files(id, name)").execute()
        return results.get("files", [])

    def download_file(self, file_id: str, destination: str) -> None:
        """Download a file from Google Drive.

        Args:
            file_id: ID of the file to download
            destination: Local path to save the file
        """
        request = self.service.files().get_media(fileId=file_id)
        with open(destination, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                print(f"Download {int(status.progress() * 100)}%.")

    def upload_file(self, file_path: str, mime_type: str) -> str:
        """Upload a file to Google Drive.

        Args:
            file_path: Path to the local file to upload
            mime_type: MIME type of the file

        Returns:
            ID of the uploaded file
        """
        file_metadata = {"name": os.path.basename(file_path)}
        media = MediaFileUpload(file_path, mimetype=mime_type)
        file = (
            self.service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        )
        return file.get("id")
