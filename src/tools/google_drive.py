import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload


SCOPES = ["https://www.googleapis.com/auth/drive"]


def authenticate_google_drive():
    """Authenticate and return the Google Drive service.

    Flow:
    1. Check if credentials.json exists
    2. Create token.json if it doesn't exist
    3. Use or refresh the token as needed
    4. Return authenticated service
    """
    # First check if credentials.json exists
    if not os.path.exists("credentials.json"):
        raise FileNotFoundError(
            "Credentials file not found. Please download it from Google Cloud Console."
        )

    creds = None
    # Check if we already have a valid token
    if os.path.exists("token.json") and os.path.getsize("token.json") > 0:
        try:
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        except Exception as e:
            print(f"Error reading token.json: {e}")
            creds = None
    else:
        creds = None

    # If no valid token, create one from credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            print("Getting new token from credentials.json...")
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
            print("Successfully obtained new token.")

        # Save the token for next time
        print("Saving token to token.json...")
        with open("token.json", "w") as token:
            token.write(creds.to_json())
        print("Token saved successfully.")

    print("Building Google Drive service...")
    return build("drive", "v3", credentials=creds)


def search_files(service, query):
    results = service.files().list(q=query, fields="files(id, name)").execute()
    return results.get("files", [])


def download_file(service, file_id, destination):
    request = service.files().get_media(fileId=file_id)
    with open(destination, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            print(f"Download {int(status.progress() * 100)}%.")


def upload_file(service, file_path, mime_type):
    file_metadata = {"name": os.path.basename(file_path)}
    media = MediaFileUpload(file_path, mimetype=mime_type)
    file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    return file.get("id")
