import unittest
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exceptions import GitHubError, GoogleDriveError
from src.execution.development_executors import (
    CreateGithubIssueExecutor,
    CreateGithubPRExecutor,
    ProcessGithubMemoriesExecutor,
    SearchGoogleDriveExecutor,
    UploadGoogleDriveExecutor,
)


class TestCreateGithubIssueExecutor(unittest.TestCase):
    def setUp(self):
        # Set up the executor with a mocked GitHub client
        self.patcher = patch("src.execution.development_executors.GitHubTool")
        self.mock_github_tool = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_github_tool.return_value = self.mock_client
        self.executor = CreateGithubIssueExecutor()

    def tearDown(self):
        self.patcher.stop()

    def test_get_required_context(self):
        """Test that required context fields are returned."""
        required = self.executor.get_required_context()
        self.assertEqual(required, ["title", "body", "labels"])

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful GitHub issue creation."""
        mock_result: Dict[str, Any] = {"number": 42, "url": "https://github.com/org/repo/issues/42"}
        self.mock_client.create_issue = AsyncMock(return_value=mock_result)

        context = {
            "title": "Test Issue",
            "body": "This is a test issue",
            "labels": ["bug", "enhancement"],
        }

        success, message = await self.executor.execute(context)

        self.assertTrue(success)
        self.assertIn("Successfully created issue #42", str(message))
        self.mock_client.create_issue.assert_called_once_with(
            "Test Issue", "This is a test issue", ["bug", "enhancement"]
        )

    @pytest.mark.asyncio
    async def test_execute_missing_context(self):
        """Test execution with missing required context."""
        context = {
            "title": "Test Issue",
            # Missing 'body'
            "labels": ["bug"],
        }

        success, message = await self.executor.execute(context)

        self.assertFalse(success)
        message_str = "" if message is None else str(message)
        self.assertIn("Missing required arguments", message_str)
        self.mock_client.create_issue.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_github_error(self):
        """Test handling of GitHub errors."""
        error_message: str = "API rate limit exceeded"
        self.mock_client.create_issue = AsyncMock(side_effect=GitHubError(error_message))

        context = {"title": "Test Issue", "body": "This is a test issue", "labels": ["bug"]}

        success, message = await self.executor.execute(context)

        self.assertFalse(success)
        message_str = "" if message is None else str(message)
        self.assertIn("Failed to create GitHub issue", message_str)
        self.assertIn("API rate limit exceeded", message_str)

    @pytest.mark.asyncio
    async def test_execute_validation_error(self):
        """Test validation error handling."""
        # Create a mock executor with a validation method that always returns False
        with patch.object(CreateGithubIssueExecutor, "validate_context", return_value=False):
            executor = CreateGithubIssueExecutor()
            context = {"title": "Test Issue"}  # Incomplete context

            success, message = await executor.execute(context)

            self.assertFalse(success)
            self.assertIsNotNone(message)
            message_str = "" if message is None else str(message)
            self.assertIn("Missing required arguments", message_str)
            self.mock_client.create_issue.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_generic_exception(self):
        """Test handling of generic exceptions."""
        # Set up mock to raise a generic exception
        self.mock_client.create_issue = AsyncMock(side_effect=Exception("Unknown error"))

        # Test with valid context
        context = {"title": "Test Issue", "body": "Issue description", "labels": ["bug"]}

        success, message = await self.executor.execute(context)

        self.assertFalse(success)
        self.assertIsNotNone(message)
        message_str = "" if message is None else str(message)
        self.assertIn("Unexpected error while creating GitHub issue", message_str)
        self.assertIn("Unknown error", message_str)
        self.mock_client.create_issue.assert_called_once()


class TestCreateGithubPRExecutor(unittest.TestCase):
    def setUp(self):
        # Set up the executor with a mocked GitHub client
        self.patcher = patch("src.execution.development_executors.GitHubTool")
        self.mock_github_tool = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_github_tool.return_value = self.mock_client
        self.executor = CreateGithubPRExecutor()

    def tearDown(self):
        self.patcher.stop()

    def test_get_required_context(self):
        """Test that required context fields are returned."""
        required = self.executor.get_required_context()
        self.assertEqual(required, ["branch", "title", "description", "files"])

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful GitHub PR creation."""
        mock_result: Dict[str, Any] = {"number": 123, "url": "https://github.com/org/repo/pull/123"}
        self.mock_client.create_pull_request = AsyncMock(return_value=mock_result)

        context = {
            "branch": "feature-branch",
            "title": "Test PR",
            "description": "This is a test PR",
            "files": [{"path": "test.py", "content": 'print("Hello")'}],
        }

        success, message = await self.executor.execute(context)

        self.assertTrue(success)
        self.assertIn("Successfully created PR #123", str(message))
        self.mock_client.create_pull_request.assert_called_once_with(
            "feature-branch", "Test PR", "This is a test PR", context["files"]
        )

    @pytest.mark.asyncio
    async def test_execute_missing_context(self):
        """Test execution with missing required context."""
        context = {
            "branch": "feature-branch",
            "title": "Test PR",
            # Missing 'description' and 'files'
        }

        success, message = await self.executor.execute(context)

        self.assertFalse(success)
        self.assertIn("Missing required arguments", str(message))
        self.mock_client.create_pull_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_github_error(self):
        """Test handling of GitHub errors."""
        error_message: str = "Branch already exists"
        self.mock_client.create_pull_request = AsyncMock(side_effect=GitHubError(error_message))

        context = {
            "branch": "feature-branch",
            "title": "Test PR",
            "description": "This is a test PR",
            "files": [{"path": "test.py", "content": 'print("Hello")'}],
        }

        success, message = await self.executor.execute(context)

        self.assertFalse(success)
        self.assertIn("Failed to create GitHub PR", str(message))
        self.assertIn("Branch already exists", str(message))


class TestProcessGithubMemoriesExecutor(unittest.TestCase):
    def setUp(self):
        # Set up the executor with a mocked GitHub client
        self.patcher = patch("src.execution.development_executors.GitHubTool")
        self.mock_github_tool = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_github_tool.return_value = self.mock_client
        self.executor = ProcessGithubMemoriesExecutor()

    def tearDown(self):
        self.patcher.stop()

    def test_get_required_context(self):
        """Test that required context fields are returned."""
        required = self.executor.get_required_context()
        self.assertEqual(required, ["file_paths", "memory_module"])

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful GitHub memory processing."""
        self.mock_client.process_files_for_memories = AsyncMock()

        memory_module = MagicMock()
        file_paths: List[str] = ["src/main.py", "tests/test_main.py"]
        context = {
            "file_paths": file_paths,
            "memory_module": memory_module,
        }

        success, message = await self.executor.execute(context)

        self.assertTrue(success)
        self.assertIn("Successfully stored 2 files", str(message))
        self.mock_client.process_files_for_memories.assert_called_once_with(
            ["src/main.py", "tests/test_main.py"], memory_module
        )

    @pytest.mark.asyncio
    async def test_execute_no_files(self):
        """Test execution with empty file list."""
        self.mock_client.process_files_for_memories = AsyncMock()

        memory_module = MagicMock()
        empty_files: List[str] = []
        context = {"file_paths": empty_files, "memory_module": memory_module}

        success, message = await self.executor.execute(context)

        self.assertFalse(success)
        self.assertIn("No files to process", str(message))
        self.mock_client.process_files_for_memories.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_missing_context(self):
        """Test execution with missing required context."""
        context = {
            # Missing 'file_paths'
            "memory_module": MagicMock()
        }

        success, message = await self.executor.execute(context)

        self.assertFalse(success)
        self.assertIn("Missing required arguments", str(message))
        self.mock_client.process_files_for_memories.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_github_error(self):
        """Test handling of GitHub errors."""
        error_message: str = "Repository not found"
        self.mock_client.process_files_for_memories = AsyncMock(
            side_effect=GitHubError(error_message)
        )

        memory_module = MagicMock()
        file_paths: List[str] = ["src/main.py"]
        context = {"file_paths": file_paths, "memory_module": memory_module}

        success, message = await self.executor.execute(context)

        self.assertFalse(success)
        self.assertIn("Failed to process GitHub memories", str(message))
        self.assertIn("Repository not found", str(message))


class TestSearchGoogleDriveExecutor(unittest.TestCase):
    def setUp(self):
        # Set up the executor with a mocked Google Drive client
        self.patcher = patch("src.execution.development_executors.GoogleDriveTool")
        self.mock_gdrive_tool = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_gdrive_tool.return_value = self.mock_client
        self.executor = SearchGoogleDriveExecutor()

    def tearDown(self):
        self.patcher.stop()

    def test_get_required_context(self):
        """Test that required context fields are returned."""
        required = self.executor.get_required_context()
        self.assertEqual(required, ["query"])

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful Google Drive search."""
        mock_results: List[Dict[str, str]] = [
            {"id": "123", "name": "doc1.txt"},
            {"id": "456", "name": "doc2.txt"},
        ]
        self.mock_client.search_files = MagicMock(return_value=mock_results)

        context: Dict[str, str] = {"query": 'name contains "doc"'}

        success, message = await self.executor.execute(context)

        self.assertTrue(success)
        self.assertIn("Found 2 matching files", str(message))
        self.mock_client.search_files.assert_called_once_with('name contains "doc"')

    @pytest.mark.asyncio
    async def test_execute_no_results(self):
        """Test search with no results."""
        empty_results: List[Dict[str, str]] = []
        self.mock_client.search_files = MagicMock(return_value=empty_results)

        context = {"query": 'name contains "nonexistent"'}

        success, message = await self.executor.execute(context)

        self.assertFalse(success)
        self.assertIn("No matching files found", str(message))
        self.mock_client.search_files.assert_called_once_with('name contains "nonexistent"')

    @pytest.mark.asyncio
    async def test_execute_missing_context(self):
        """Test execution with missing required context."""
        context: Dict[str, Any] = {}  # Missing 'query'

        success, message = await self.executor.execute(context)

        self.assertFalse(success)
        self.assertIn("Missing required query", str(message))
        self.mock_client.search_files.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_gdrive_error(self):
        """Test handling of Google Drive errors."""
        error_message: str = "API error"
        self.mock_client.search_files = MagicMock(side_effect=GoogleDriveError(error_message))

        context = {"query": 'name contains "doc"'}

        success, message = await self.executor.execute(context)

        self.assertFalse(success)
        self.assertIn("Failed to search Google Drive", str(message))
        self.assertIn("API error", str(message))


class TestUploadGoogleDriveExecutor(unittest.TestCase):
    def setUp(self):
        # Set up the executor with a mocked Google Drive client
        self.patcher = patch("src.execution.development_executors.GoogleDriveTool")
        self.mock_gdrive_tool = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_gdrive_tool.return_value = self.mock_client
        self.executor = UploadGoogleDriveExecutor()

    def tearDown(self):
        self.patcher.stop()

    def test_get_required_context(self):
        """Test that required context fields are returned."""
        required = self.executor.get_required_context()
        self.assertEqual(required, ["file_path", "mime_type"])

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful Google Drive upload."""
        file_id: str = "file_id_123"
        self.mock_client.upload_file = MagicMock(return_value=file_id)

        context = {"file_path": "/path/to/document.pdf", "mime_type": "application/pdf"}

        success, message = await self.executor.execute(context)

        self.assertTrue(success)
        self.assertIn("Successfully uploaded file with ID: file_id_123", str(message))
        self.mock_client.upload_file.assert_called_once_with(
            "/path/to/document.pdf", "application/pdf"
        )

    @pytest.mark.asyncio
    async def test_execute_upload_failure(self):
        """Test when upload returns no file ID."""
        self.mock_client.upload_file = MagicMock(return_value=None)

        context = {"file_path": "/path/to/document.pdf", "mime_type": "application/pdf"}

        success, message = await self.executor.execute(context)

        self.assertFalse(success)
        self.assertIn("Failed to upload file to Google Drive", str(message))
        self.mock_client.upload_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_missing_context(self):
        """Test execution with missing required context."""
        context = {
            "file_path": "/path/to/document.pdf",
            # Missing 'mime_type'
        }

        success, message = await self.executor.execute(context)

        self.assertFalse(success)
        self.assertIn("Missing required file_path or mime_type", str(message))
        self.mock_client.upload_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_gdrive_error(self):
        """Test handling of Google Drive errors."""
        error_message: str = "File too large"
        self.mock_client.upload_file = MagicMock(side_effect=GoogleDriveError(error_message))

        context = {"file_path": "/path/to/large_file.zip", "mime_type": "application/zip"}

        success, message = await self.executor.execute(context)

        self.assertFalse(success)
        self.assertIn("Failed to upload to Google Drive", str(message))
        self.assertIn("File too large", str(message))


if __name__ == "__main__":
    unittest.main()
