from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from src.core.exceptions import GitHubError, GoogleDriveError
from src.execution.base import ActionExecutor
from src.tools.github import GitHubTool
from src.tools.google_drive import GoogleDriveTool


class CreateGithubIssueExecutor(ActionExecutor):
    """Executor for creating GitHub issues."""

    def __init__(self):
        super().__init__()
        self.client = self._initialize_client()

    def _initialize_client(self) -> GitHubTool:
        """Initialize GitHub tool client."""
        return GitHubTool()

    def get_required_context(self) -> List[str]:
        """Get required context fields."""
        return ["title", "body", "labels"]

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute GitHub issue creation."""
        try:
            if not self.validate_context(context):
                return False, "Missing required arguments in context"

            title = context.get("title")
            body = context.get("body")
            labels = context.get("labels", [])

            logger.info(f"Creating GitHub issue: {title}")
            result = await self.client.create_issue(title, body, labels)

            if result:
                return True, f"Successfully created issue #{result['number']}: {result['url']}"
            return False, "Failed to create GitHub issue"

        except GitHubError as e:
            error_msg = f"Failed to create GitHub issue: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error while creating GitHub issue: {str(e)}"
            logger.error(error_msg)
            return False, error_msg


class CreateGithubPRExecutor(ActionExecutor):
    """Executor for creating GitHub pull requests."""

    def __init__(self):
        super().__init__()
        self.client = self._initialize_client()

    def _initialize_client(self) -> GitHubTool:
        """Initialize GitHub tool client."""
        return GitHubTool()

    def get_required_context(self) -> List[str]:
        """Get required context fields."""
        return ["branch", "title", "description", "files"]

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute GitHub PR creation."""
        try:
            if not self.validate_context(context):
                return False, "Missing required arguments in context"

            branch = context.get("branch")
            title = context.get("title")
            description = context.get("description")
            files = context.get("files")

            logger.info(f"Creating GitHub PR: {title}")
            result = await self.client.create_pull_request(branch, title, description, files)

            if result:
                return True, f"Successfully created PR #{result['number']}: {result['url']}"
            return False, "Failed to create GitHub PR"

        except GitHubError as e:
            error_msg = f"Failed to create GitHub PR: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error while creating GitHub PR: {str(e)}"
            logger.error(error_msg)
            return False, error_msg


class ProcessGithubMemoriesExecutor(ActionExecutor):
    """Executor for processing GitHub files into memories."""

    def __init__(self):
        super().__init__()
        self.client = self._initialize_client()

    def _initialize_client(self) -> GitHubTool:
        """Initialize GitHub tool client."""
        return GitHubTool()

    def get_required_context(self) -> List[str]:
        """Get required context fields."""
        return ["file_paths", "memory_module"]

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute GitHub memory processing."""
        try:
            if not self.validate_context(context):
                return False, "Missing required arguments in context"

            file_paths = context.get("file_paths")
            memory_module = context.get("memory_module")

            logger.info("Processing GitHub files into memories")
            if file_paths:
                await self.client.process_files_for_memories(file_paths, memory_module)
                return True, f"Successfully stored {len(file_paths)} files into memories"
            return False, "No files to process"

        except GitHubError as e:
            error_msg = f"Failed to process GitHub memories: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error while processing GitHub memories: {str(e)}"
            logger.error(error_msg)
            return False, error_msg


class SearchGoogleDriveExecutor(ActionExecutor):
    """Executor for searching files in Google Drive."""

    def __init__(self):
        super().__init__()
        self.client = self._initialize_client()

    def _initialize_client(self) -> GoogleDriveTool:
        """Initialize Google Drive tool client."""
        return GoogleDriveTool()

    def get_required_context(self) -> List[str]:
        """Get required context fields."""
        return ["query"]

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute Google Drive search."""
        try:
            if not self.validate_context(context):
                return False, "Missing required query in context"

            query = context.get("query")
            logger.info(f"Searching Google Drive for: {query}")
            results = self.client.search_files(query)

            if results:
                return True, f"Found {len(results)} matching files"
            return False, "No matching files found"

        except GoogleDriveError as e:
            error_msg = f"Failed to search Google Drive: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error while searching Google Drive: {str(e)}"
            logger.error(error_msg)
            return False, error_msg


class UploadGoogleDriveExecutor(ActionExecutor):
    """Executor for uploading files to Google Drive."""

    def __init__(self):
        super().__init__()
        self.client = self._initialize_client()

    def _initialize_client(self) -> GoogleDriveTool:
        """Initialize Google Drive tool client."""
        return GoogleDriveTool()

    def get_required_context(self) -> List[str]:
        """Get required context fields."""
        return ["file_path", "mime_type"]

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute Google Drive file upload."""
        try:
            if not self.validate_context(context):
                return False, "Missing required file_path or mime_type in context"

            file_path = context.get("file_path")
            mime_type = context.get("mime_type")

            logger.info(f"Uploading file to Google Drive: {file_path}")
            file_id = self.client.upload_file(file_path, mime_type)

            if file_id:
                return True, f"Successfully uploaded file with ID: {file_id}"
            return False, "Failed to upload file to Google Drive"

        except GoogleDriveError as e:
            error_msg = f"Failed to upload to Google Drive: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error while uploading to Google Drive: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
