# import os
# import shutil
# import tempfile
# from pathlib import Path
# from unittest.mock import AsyncMock, Mock, patch

# import pytest
# from git import Repo
# from github import Repository

# from src.core.exceptions import GitHubError
# from src.tools.github import FileChange, GitHubIntegration


# @pytest.fixture
# def temp_dir():
#     """Create a temporary directory for repo operations."""
#     tmp_dir = tempfile.mkdtemp()
#     yield tmp_dir
#     shutil.rmtree(tmp_dir)


# @pytest.fixture
# def github_integration(temp_dir):
#     """Create GitHubIntegration instance with mocked dependencies."""
#     with patch("src.tools.github.Github"):
#         integration = GitHubIntegration(token="test_token", cache_dir=temp_dir)
#         yield integration


# @pytest.fixture
# def mock_repo(temp_dir):
#     """Create a mock Git repository."""
#     mock = Mock(spec=Repo)
#     mock.working_dir = temp_dir
#     mock.active_branch = Mock()
#     mock.active_branch.name = "main"
#     mock.remotes.origin = Mock()
#     mock.git = Mock()
#     mock.index = Mock()
#     mock.create_head = Mock(return_value=Mock(checkout=Mock()))
#     return mock


# @pytest.fixture
# def mock_gh_repo():
#     """Create a mock GitHub repository."""
#     mock = Mock(spec=Repository)
#     mock.clone_url = "https://github.com/test/repo.git"
#     # Add proper create_pull method
#     mock.create_pull = Mock(
#         return_value=Mock(number=1, html_url="https://github.com/test/pr/1", title="Test PR")
#     )
#     return mock


# @pytest.mark.asyncio
# async def test_initialize_repo_new(github_integration, mock_gh_repo):
#     """Test initializing a new repository."""
#     with patch("src.tools.github.Repo") as mock_repo_class:
#         # Setup mocks
#         github_integration.github.get_repo.return_value = mock_gh_repo
#         mock_repo_instance = Mock()
#         mock_repo_class.clone_from.return_value = mock_repo_instance

#         # Test initialization
#         await github_integration.initialize_repo("owner", "repo")

#         # Verify
#         github_integration.github.get_repo.assert_called_with("owner/repo")
#         mock_repo_class.clone_from.assert_called_once()
#         mock_repo_instance.git.checkout.assert_called_with("main")


# @pytest.mark.asyncio
# async def test_initialize_repo_existing(github_integration, mock_gh_repo, temp_dir):
#     """Test initializing an existing repository."""
#     with patch("src.tools.github.Repo") as mock_repo_class:
#         # Create existing repo directory
#         repo_path = Path(temp_dir) / "owner_repo"
#         repo_path.mkdir()

#         # Setup mocks
#         github_integration.github.get_repo.return_value = mock_gh_repo
#         mock_repo_instance = Mock()
#         mock_repo_class.return_value = mock_repo_instance

#         # Test initialization
#         await github_integration.initialize_repo("owner", "repo")

#         # Verify
#         mock_repo_class.assert_called_with(repo_path)
#         mock_repo_instance.git.checkout.assert_called_with("main")


# @pytest.mark.asyncio
# async def test_update_repo(github_integration, mock_repo):
#     """Test repository update functionality."""
#     github_integration.current_repo = mock_repo

#     await github_integration.update_repo()

#     mock_repo.remotes.origin.pull.assert_called_once()


# @pytest.mark.asyncio
# async def test_process_files_for_memories(github_integration, mock_repo, temp_dir):
#     """Test processing files for memories."""
#     # Setup
#     github_integration.current_repo = mock_repo
#     mock_memory_module = AsyncMock()  # Use AsyncMock for async methods
#     mock_memory_module.exists.return_value = False

#     # Create actual test file
#     test_file_path = os.path.join(temp_dir, "test.txt")
#     with open(test_file_path, "w") as f:
#         f.write("test content")

#     # Test
#     await github_integration.process_files_for_memories(["test.txt"], mock_memory_module)

#     # Verify
#     mock_memory_module.store.assert_called_once()
#     stored_data = mock_memory_module.store.call_args[0][0]
#     assert stored_data["type"] == "file"
#     assert stored_data["path"] == "test.txt"
#     assert stored_data["content"] == "test content"


# @pytest.mark.asyncio
# async def test_create_pull_request(github_integration, mock_repo, mock_gh_repo, temp_dir):
#     """Test pull request creation."""
#     # Setup
#     github_integration.current_repo = mock_repo
#     github_integration.current_gh_repo = mock_gh_repo

#     files = [FileChange(path="test.txt", content="test content")]

#     # Create the test file directory if it doesn't exist
#     test_file_dir = os.path.join(temp_dir, os.path.dirname(files[0].path))
#     os.makedirs(test_file_dir, exist_ok=True)

#     # Test
#     result = await github_integration.create_pull_request(
#         branch="feature", title="Test PR", description="Test description", files=files
#     )

#     # Verify
#     assert result["number"] == 1
#     assert result["url"] == "https://github.com/test/pr/1"
#     mock_repo.create_head.assert_called_with("feature")
#     mock_repo.index.commit.assert_called_once()
#     mock_repo.remotes.origin.push.assert_called_once()
#     mock_gh_repo.create_pull.assert_called_once_with(
#         title="Test PR", body="Test description", head="feature", base="main"
#     )


# @pytest.mark.asyncio
# async def test_create_commit(github_integration, mock_repo, temp_dir):
#     """Test commit creation."""
#     # Setup
#     github_integration.current_repo = mock_repo
#     files = [FileChange(path="test.txt", content="test content")]

#     # Create the test file directory if it doesn't exist
#     test_file_dir = os.path.join(temp_dir, os.path.dirname(files[0].path))
#     os.makedirs(test_file_dir, exist_ok=True)

#     # Test
#     await github_integration.create_commit(branch="main", message="Test commit", files=files)

#     # Verify
#     mock_repo.git.checkout.assert_called_with("main")
#     mock_repo.index.commit.assert_called_with("Test commit")
#     mock_repo.remotes.origin.push.assert_called_once()


# @pytest.mark.asyncio
# async def test_error_handling(github_integration):
#     """Test error handling for uninitialized operations."""
#     with pytest.raises(GitHubError):
#         await github_integration.update_repo()

#     with pytest.raises(GitHubError):
#         await github_integration.create_pull_request(
#             branch="test", title="test", description="test", files=[]
#         )

#     with pytest.raises(GitHubError):
#         await github_integration.create_commit(branch="test", message="test", files=[])


# @pytest.mark.asyncio
# async def test_initialize_repo_failure(github_integration):
#     """Test repository initialization failure."""
#     github_integration.github.get_repo.side_effect = Exception("API Error")

#     with pytest.raises(GitHubError) as exc_info:
#         await github_integration.initialize_repo("owner", "repo")

#     assert "Failed to initialize repo" in str(exc_info.value)
