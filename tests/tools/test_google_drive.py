# import unittest
# from unittest.mock import Mock, patch

# from src.tools.google_drive import (
#     authenticate_google_drive,
#     download_file,
#     search_files,
#     upload_file,
# )


# class TestGoogleDrive(unittest.TestCase):
#     def setUp(self):
#         # Mock the credentials and service for each test
#         self.mock_creds = Mock()
#         self.mock_service = Mock()

#     @patch("src.tools.google_drive.Credentials")
#     @patch("src.tools.google_drive.build")
#     @patch("os.path.exists")
#     @patch("os.path.getsize")
#     def test_authenticate_with_existing_token(
#         self, mock_getsize, mock_exists, mock_build, mock_credentials
#     ):
#         # Setup mocks
#         mock_exists.return_value = True
#         mock_getsize.return_value = 100
#         mock_credentials.from_authorized_user_file.return_value = self.mock_creds
#         self.mock_creds.valid = True
#         mock_build.return_value = self.mock_service

#         # Test authentication
#         service = authenticate_google_drive()

#         # Verify the expected calls
#         mock_credentials.from_authorized_user_file.assert_called_once_with(
#             "token.json", ["https://www.googleapis.com/auth/drive"]
#         )
#         mock_build.assert_called_once_with("drive", "v3", credentials=self.mock_creds)
#         self.assertEqual(service, self.mock_service)

#     def test_search_files(self):
#         # Setup mock response
#         mock_response = {
#             "files": [{"id": "123", "name": "test1.txt"}, {"id": "456", "name": "test2.txt"}]
#         }
#         self.mock_service.files().list().execute.return_value = mock_response

#         # Test search_files
#         results = search_files(self.mock_service, "name contains 'test'")

#         # Verify results
#         self.assertEqual(len(results), 2)
#         self.assertEqual(results[0]["id"], "123")
#         self.assertEqual(results[1]["name"], "test2.txt")

#     @patch("builtins.open")
#     def test_download_file(self, mock_open):
#         # Setup mock downloader
#         mock_downloader = Mock()
#         mock_downloader.next_chunk.side_effect = [
#             (Mock(progress=lambda: 0.5), False),
#             (Mock(progress=lambda: 1.0), True),
#         ]

#         self.mock_service.files().get_media.return_value = Mock()

#         # Patch MediaIoBaseDownload to return our mock_downloader
#         with patch("src.tools.google_drive.MediaIoBaseDownload", return_value=mock_downloader):
#             download_file(self.mock_service, "test_file_id", "test_destination.txt")

#         # Verify the file was opened and downloader was called twice
#         mock_open.assert_called_once_with("test_destination.txt", "wb")
#         self.assertEqual(mock_downloader.next_chunk.call_count, 2)

#     def test_upload_file(self):
#         # Setup mock chain
#         mock_files = Mock()
#         mock_create = Mock()
#         self.mock_service.files.return_value = mock_files
#         mock_files.create.return_value = mock_create
#         mock_create.execute.return_value = {"id": "uploaded_file_id"}

#         # Patch MediaFileUpload
#         with patch("src.tools.google_drive.MediaFileUpload") as mock_media_upload:
#             file_id = upload_file(self.mock_service, "test.txt", "text/plain")

#         # Verify the upload
#         self.assertEqual(file_id, "uploaded_file_id")
#         mock_media_upload.assert_called_once_with("test.txt", mimetype="text/plain")
#         mock_files.create.assert_called_once()


# if __name__ == "__main__":
#     unittest.main()
