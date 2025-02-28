# GitHub Integration

## Setup

1. Generate GitHub Personal Access Token
   - Go to [GitHub Settings](https://github.com/settings/tokens)
   - Click "Generate new token" > "Generate new token (classic)"
   - Select required scopes:
     - `repo` (Full control of private repositories)
     - `workflow` (Optional: for workflow actions)
   - Copy the generated token

2. Configure Environment Variables
   Add these to your `.env` file:
   ```bash
   GITHUB_TOKEN=your_personal_access_token_here
   ```

### Basic Setup
```python
from src.tools.github import GitHubIntegration, FileChange

# Initialize GitHub client
github = GitHubIntegration()

# Initialize repository
await github.initialize_repo(
    owner="username",
    repo_name="repository",
    branch="main"
)

# Create a pull request
files = [
    FileChange(
        path="path/to/file.py",
        content="Updated file content"
    )
]

pr = await github.create_pull_request(
    branch="feature-branch",
    title="Add new feature",
    description="Implemented new functionality",
    files=files
)

# Create a direct commit
await github.create_commit(
    branch="main",
    message="Update documentation",
    files=files
)
```

## Features
- Repository initialization and management
- File content processing and memory storage
- Pull request creation with multiple file changes
- Direct commit creation
- Automatic branch management
- Local repository caching
- Repository synchronization

## TODOs for Future Enhancements:
- Add support for GitHub Actions workflow management
- Implement issue creation and management
- Implement code review automation
- Add support for GitHub Projects & Packages
- Implement repository statistics and analytics
- Implement repository security scanning
- Handle GitHub webhook events (e.g., new commits, pull requests) for real-time agent updates
- Enable metadata-based memory filtering for selective file processing
- Implement branch management and conflict resolution
- Add support for attachments and binary files
- Optimize performance for large repositories

## Reference
For implementation details, see: `src/tools/github.py`

The implementation uses the PyGithub library. For more information, refer to:
- [PyGithub Documentation](https://pygithub.readthedocs.io/)
- [GitHub REST API Documentation](https://docs.github.com/en/rest)
