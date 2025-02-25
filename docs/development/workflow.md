# Development Workflow

## Code Style

Follow the [Code Style and Standards](contributing.md#code-style-and-standards) section.

## Testing

### Writing Tests
- Place tests in the `tests/` directory
- Follow the same directory structure as the source code
- Name test files with `test_` prefix
- Use pytest fixtures for common setup
- Aim for 100% test coverage for new code

### Running Tests
```bash
# Run all tests
make test

# Run specific test file
pipenv run pytest tests/path/to/test_file.py

# Run with coverage
make coverage
```

## Debugging

### Local Debugging
1. Use Python debugger (pdb):
```python
import pdb; pdb.set_trace()
```

2. VSCode debugging:
   - Set breakpoints in the editor
   - Use the Run and Debug panel
   - Configure `launch.json` for your specific needs

### Logging
- Use the loguru module
- Configure log levels appropriately (debug, info, warning, error, critical)

## GitHub Workflows

The project uses several GitHub Actions workflows:

### Main Workflow (`main.yml`)
- Runs on every push and pull request
- Performs linting and testing
- Checks code formatting
- Generates coverage report

### Documentation Workflow (`deploy-docs.yml`)
- Builds and deploys documentation to GitHub Pages
- Triggers on pushes to main branch
- Uses MkDocs Material theme

### Docker Workflow (`docker.yml`)
- Builds and pushes Docker images
- Runs on releases and main branch pushes
- Tags images appropriately

## Release Process

The maintainer reviews and publishes releases manually!