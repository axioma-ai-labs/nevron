# Development Setup

## Prerequisites

- Python 3.12+
- pipenv
- make (for using Makefile commands)
- git

## Initial Setup

1. Clone the repository:
```bash
git clone https://github.com/axioma-ai-labs/nevron.git
cd nevron
```

2. Install dependencies:
```bash
make deps
```

This will:
- Install pipenv if not present
- Install all project dependencies
- Set up pre-commit hooks

## Environment Setup

The project uses pipenv for dependency management. Key commands:

```bash
# Activate virtual environment
pipenv shell

# Install a new package
pipenv install package_name

# Install a development package
pipenv install --dev package_name
```

## IDE Setup

### VSCode
Recommended extensions:
- Python
- ruff
- isort
- GitLens

Recommended settings (`settings.json`):
```json
{
    "python.formatting.provider": "ruff",
    "editor.formatOnSave": true,
    "python.linting.enabled": true,
    "python.linting.mypyEnabled": true
}
```

### PyCharm
- Enable ruff formatter
- Set Python interpreter to the pipenv environment
- Enable mypy for type checking