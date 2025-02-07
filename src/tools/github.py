import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

from git import Repo
from github import Github
from github.Repository import Repository
from loguru import logger
from pydantic import BaseModel

from src.core.config import settings
from src.core.exceptions import GitHubError


class FileChange(BaseModel):
    """Model for file changes in GitHub operations."""

    path: str
    content: str
    mode: str = "100644"  # Default file mode


class GitHubTool:
    """GitHub integration for Nevron framework."""

    def __init__(self, token: str = settings.GITHUB_TOKEN, cache_dir: str = ".nevron/repos"):
        """Initialize GitHub integration tool.

        Args:
            token: GitHub access token
            cache_dir: Directory to store cloned repositories
        """
        self.github = Github(token)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.current_repo: Optional[Repo] = None
        self.current_gh_repo: Optional[Repository] = None

    async def initialize_repo(self, owner: str, repo_name: str, branch: str = "main") -> None:
        """Clone and initialize a GitHub repository.

        Args:
            owner: Repository owner
            repo_name: Repository name
            branch: Branch to checkout
        """
        try:
            # Get GitHub repo
            self.current_gh_repo = self.github.get_repo(f"{owner}/{repo_name}")

            # Setup local repo path
            repo_path = self.cache_dir / f"{owner}_{repo_name}"

            if repo_path.exists():
                self.current_repo = Repo(repo_path)
                await self.update_repo()
            else:
                clone_url = self.current_gh_repo.clone_url
                self.current_repo = Repo.clone_from(clone_url, repo_path)

            # Checkout specified branch
            self.current_repo.git.checkout(branch)

            logger.info(f"Initialized repo {owner}/{repo_name} on branch {branch}")

        except Exception as e:
            raise GitHubError(f"Failed to initialize repo: {str(e)}")

    async def update_repo(self) -> None:
        """Pull latest changes from remote repository."""
        if not self.current_repo:
            raise GitHubError("No repository initialized")

        try:
            self.current_repo.remotes.origin.pull()
            logger.info("Repository updated successfully")
        except Exception as e:
            raise GitHubError(f"Failed to update repo: {str(e)}")

    async def process_files_for_memories(
        self,
        file_paths: List[str],
        memory_module: Any,  # Replace with actual memory module type
    ) -> None:
        """Process repository files and store as agent memories.

        Args:
            file_paths: List of file paths to process
            memory_module: Memory module instance for storing memories
        """
        if not self.current_repo:
            raise GitHubError("No repository initialized")

        for file_path in file_paths:
            try:
                full_path = Path(self.current_repo.working_dir) / file_path
                if not full_path.exists():
                    logger.warning(f"File not found: {file_path}")
                    continue

                content = full_path.read_text()
                file_hash = hashlib.sha256(content.encode()).hexdigest()

                # Store in memory if not exists
                if not await memory_module.exists(file_hash):
                    await memory_module.store(
                        {"type": "file", "path": file_path, "content": content, "hash": file_hash}
                    )
                    logger.info(f"Stored memory for file: {file_path}")

            except Exception as e:
                logger.error(f"Failed to process file {file_path}: {str(e)}")

    async def create_pull_request(
        self, branch: str, title: str, description: str, files: List[FileChange]
    ) -> Dict:
        """Create a pull request with file changes.

        Args:
            branch: New branch name for changes
            title: PR title
            description: PR description
            files: List of file changes

        Returns:
            Dict containing PR details
        """
        if not (self.current_repo and self.current_gh_repo):
            raise GitHubError("No repository initialized")

        try:
            # Create and checkout new branch
            current = self.current_repo.active_branch
            new_branch = self.current_repo.create_head(branch)
            new_branch.checkout()

            # Apply file changes
            for file_change in files:
                file_path = Path(self.current_repo.working_dir) / file_change.path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(file_change.content)
                self.current_repo.index.add([file_change.path])

            # Commit and push
            self.current_repo.index.commit(f"feat: {title}")
            self.current_repo.remotes.origin.push(branch)

            # Create PR
            pr = self.current_gh_repo.create_pull(
                title=title, body=description, head=branch, base=current.name
            )

            logger.info(f"Created PR #{pr.number}: {title}")
            return {"number": pr.number, "url": pr.html_url, "title": pr.title}

        except Exception as e:
            raise GitHubError(f"Failed to create PR: {str(e)}")
        finally:
            # Return to original branch
            current.checkout()

    async def create_commit(self, branch: str, message: str, files: List[FileChange]) -> None:
        """Create a commit with file changes.

        Args:
            branch: Branch to commit to
            message: Commit message
            files: List of file changes
        """
        if not self.current_repo:
            raise GitHubError("No repository initialized")

        try:
            # Checkout target branch
            self.current_repo.git.checkout(branch)

            # Apply file changes
            for file_change in files:
                file_path = Path(self.current_repo.working_dir) / file_change.path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(file_change.content)
                self.current_repo.index.add([file_change.path])

            # Commit and push
            self.current_repo.index.commit(message)
            self.current_repo.remotes.origin.push()

            logger.info(f"Created commit on {branch}: {message}")

        except Exception as e:
            raise GitHubError(f"Failed to create commit: {str(e)}")

    async def create_issue(self, title: str, body: str, labels: Optional[List[str]] = None) -> Dict:
        """Create a new issue in the current repository.

        Args:
            title: Issue title
            body: Issue description
            labels: Optional list of labels to apply to the issue

        Returns:
            Dict containing issue details

        Raises:
            GitHubError: If no repository is initialized or if issue creation fails
        """
        if not self.current_gh_repo:
            raise GitHubError("No repository initialized")

        try:
            issue = self.current_gh_repo.create_issue(title=title, body=body, labels=labels or [])
            logger.info(f"Created issue #{issue.number}: {title}")
            return {
                "number": issue.number,
                "url": issue.html_url,
                "title": issue.title,
                "state": issue.state,
            }
        except Exception as e:
            raise GitHubError(f"Failed to create issue: {str(e)}")
