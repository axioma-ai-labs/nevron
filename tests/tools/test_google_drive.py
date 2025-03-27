import unittest
from unittest.mock import MagicMock, patch

from src.tools.google_drive import GoogleDriveTool


class TestGoogleDriveTool(unittest.TestCase):
    def setUp(self):
        # Create a mock service for each test
        self.mock_service = MagicMock()
        self.mock_creds = MagicMock()

        # Patch the initialization to avoid trying to load real credentials
        patcher = patch.object(GoogleDriveTool, "__init__", return_value=None)
        self.mock_init = patcher.start()
        self.addCleanup(patcher.stop)

        # Create tool and manually set its service attribute
        self.tool = GoogleDriveTool()
        self.tool.service = self.mock_service

    @patch("src.tools.google_drive.Credentials")
    @patch("src.tools.google_drive.build")
    @patch("os.path.exists")
    @patch("os.path.getsize")
    def test_authenticate_success(self, mock_getsize, mock_exists, mock_build, mock_credentials):
        """Test successful authentication."""
        # Setup mocks
        # First, mock os.path.exists to return True for both credentials.json and token.json
        mock_exists.side_effect = lambda path: True

        # Mock token.json file size to be non-empty
        mock_getsize.return_value = 100

        # Setup credentials mock
        mock_credentials.from_authorized_user_file.return_value = self.mock_creds
        self.mock_creds.valid = True

        # Setup service mock
        mock_build.return_value = self.mock_service

        # Create a fresh instance and directly test the _authenticate method
        tool = GoogleDriveTool.__new__(GoogleDriveTool)  # Create instance without calling __init__
        service = tool._authenticate()

        # Verify the expected calls
        mock_credentials.from_authorized_user_file.assert_called_once_with(
            "token.json", ["https://www.googleapis.com/auth/drive"]
        )
        mock_build.assert_called_once_with("drive", "v3", credentials=self.mock_creds)
        self.assertEqual(service, self.mock_service)

    @patch("os.path.exists")
    def test_authenticate_failure(self, mock_exists):
        """Test authentication failure when credentials file is missing."""
        # Set up mock to return False for credentials.json specifically
        mock_exists.return_value = False  # Simply return False for all path checks

        # Create a new instance and directly test the _authenticate method
        tool = GoogleDriveTool.__new__(GoogleDriveTool)  # Create instance without calling __init__

        # Test the _authenticate method directly
        with self.assertRaises(FileNotFoundError):
            tool._authenticate()

    def test_search_files(self):
        """Test successful file search."""
        # Setup mock response
        mock_response = {
            "files": [{"id": "123", "name": "test1.txt"}, {"id": "456", "name": "test2.txt"}]
        }

        # Setup mock chain for files().list().execute()
        mock_files = MagicMock()
        mock_list = MagicMock()

        self.mock_service.files.return_value = mock_files
        mock_files.list.return_value = mock_list
        mock_list.execute.return_value = mock_response

        # Test search_files
        results = self.tool.search_files("name contains 'test'")

        # Verify results
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["id"], "123")
        self.assertEqual(results[1]["name"], "test2.txt")

    @patch("builtins.open")
    def test_download_file(self, mock_open):
        """Test successful file download."""
        # Setup mock downloader
        mock_downloader = MagicMock()
        mock_downloader.next_chunk.side_effect = [
            (MagicMock(progress=lambda: 0.5), False),
            (MagicMock(progress=lambda: 1.0), True),
        ]

        # Setup mock chain for files().get_media()
        mock_files = MagicMock()
        mock_get_media = MagicMock()

        self.mock_service.files.return_value = mock_files
        mock_files.get_media.return_value = mock_get_media

        # Patch MediaIoBaseDownload to return our mock_downloader
        with patch("src.tools.google_drive.MediaIoBaseDownload", return_value=mock_downloader):
            self.tool.download_file("test_file_id", "test_destination.txt")

        # Verify the file was opened and downloader was called twice
        mock_open.assert_called_once_with("test_destination.txt", "wb")
        self.assertEqual(mock_downloader.next_chunk.call_count, 2)

    @patch("src.tools.google_drive.MediaFileUpload")
    def test_upload_file(self, mock_media_upload):
        """Test successful file upload."""
        # Setup mock chain
        mock_files = MagicMock()
        mock_create = MagicMock()

        self.mock_service.files.return_value = mock_files
        mock_files.create.return_value = mock_create
        mock_create.execute.return_value = {"id": "uploaded_file_id"}

        # Test upload
        file_id = self.tool.upload_file("test.txt", "text/plain")

        # Verify the upload
        self.assertEqual(file_id, "uploaded_file_id")
        mock_media_upload.assert_called_once_with("test.txt", mimetype="text/plain")
        mock_files.create.assert_called_once()

    @patch("src.tools.google_drive.MediaFileUpload")
    def test_upload_file_failure(self, mock_media_upload):
        """Test file upload failure."""
        # Setup mock chain
        mock_files = MagicMock()
        mock_create = MagicMock()

        self.mock_service.files.return_value = mock_files
        mock_files.create.return_value = mock_create
        mock_create.execute.side_effect = Exception("Upload failed")

        # Test upload
        with self.assertRaises(Exception):
            self.tool.upload_file("test.txt", "text/plain")

    @patch("builtins.open")
    def test_download_file_failure(self, mock_open):
        """Test file download failure."""
        # Setup mock downloader
        mock_downloader = MagicMock()
        mock_downloader.next_chunk.side_effect = Exception("Download failed")

        # Setup mock chain for files().get_media()
        mock_files = MagicMock()
        mock_get_media = MagicMock()

        self.mock_service.files.return_value = mock_files
        mock_files.get_media.return_value = mock_get_media

        # Patch MediaIoBaseDownload to return our mock_downloader
        with patch("src.tools.google_drive.MediaIoBaseDownload", return_value=mock_downloader):
            with self.assertRaises(Exception):
                self.tool.download_file("test_file_id", "test_destination.txt")
