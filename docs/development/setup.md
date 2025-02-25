# Development Setup

This guide provides detailed instructions for setting up a development environment for Nevron.

## Prerequisites

- **Python 3.13+** (required for the latest features and optimizations)
- **Poetry** (for dependency management)
- **Make** (for using Makefile commands)
- **Git** (for version control)
- **Docker** (optional, for containerized development)

## Initial Setup

### 1. Clone the Repository

```bash
git clone https://github.com/axioma-ai-labs/nevron.git
cd nevron
```

### 2. Install Poetry

If you haven't installed Poetry yet:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Make sure to add Poetry to your PATH according to the installation instructions.

### 3. Install Dependencies

```bash
make deps
```

This will:
- Install all project dependencies using Poetry
- Set up pre-commit hooks for code quality
- Configure the development environment

## Environment Configuration

### Basic Configuration

Create a development environment file:

```bash
cp .env.dev .env
```

### LLM Provider Configuration

You have several options for configuring the LLM provider:

#### Option 1: Use a Third-Party LLM API

Edit your `.env` file to include one of these LLM providers:

```bash
# OpenAI
OPENAI_API_KEY=your_key_here
LLM_PROVIDER=openai

# Anthropic
ANTHROPIC_API_KEY=your_key_here
LLM_PROVIDER=anthropic

# xAI (Grok)
XAI_API_KEY=your_key_here
LLM_PROVIDER=xai

# DeepSeek
DEEPSEEK_API_KEY=your_key_here
LLM_PROVIDER=deepseek

# Qwen
QWEN_API_KEY=your_key_here
LLM_PROVIDER=qwen

# Venice
VENICE_API_KEY=your_key_here
LLM_PROVIDER=venice
```

#### Option 2: Use Llama via API Services

```bash
# Standard Llama API
LLAMA_PROVIDER=llama-api
LLAMA_API_KEY=your_key_here
LLM_PROVIDER=llama

# OpenRouter
LLAMA_PROVIDER=openrouter
LLAMA_API_KEY=your_key_here
LLM_PROVIDER=llama

# Fireworks
LLAMA_PROVIDER=fireworks
LLAMA_API_KEY=your_key_here
LLM_PROVIDER=llama
```

#### Option 3: Run Ollama Locally (Recommended for Development)

1. Install Ollama following the instructions at [ollama.ai](https://ollama.ai)

2. Pull a small model:
```bash
ollama pull llama3:8b-instruct
```

3. Configure your `.env` file:
```bash
LLM_PROVIDER=llama
LLAMA_PROVIDER=ollama
LLAMA_OLLAMA_MODEL=llama3:8b-instruct
```

### Memory Configuration

For development, you can use either ChromaDB (default) or Qdrant:

```bash
# ChromaDB (lightweight, file-based)
MEMORY_BACKEND_TYPE=chroma

# Qdrant (requires running Qdrant server)
MEMORY_BACKEND_TYPE=qdrant
MEMORY_HOST=localhost
MEMORY_PORT=6333
```

## Running the Application

### Start the Development Server

```bash
make run
```

### Run Tests

```bash
make test
```

### Lint Code

```bash
make lint
```

### Format Code

```bash
make format
```

## IDE Setup

### VSCode

Recommended extensions:
- Python
- Ruff
- isort
- GitLens
- Poetry

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

- Enable Ruff formatter
- Set Python interpreter to the Poetry environment
- Enable mypy for type checking
- Configure Poetry as the package manager

## Troubleshooting

Common development issues:

- **Python Version**: Ensure you're using Python 3.13+
  ```bash
  python --version
  ```

- **Poetry Environment**: Verify Poetry has created the virtual environment
  ```bash
  poetry env info
  ```

- **Dependencies**: Check installed packages
  ```bash
  poetry show
  ```

- **Ollama**: If using Ollama, verify it's running
  ```bash
  ollama list
  ```

- **Environment Variables**: Ensure your `.env` file contains the necessary configuration
  ```bash
  cat .env | grep -v "^#" | grep .
  ```

- **Logs**: Check the application logs for detailed error messages
  ```bash
  tail -f logs/app.log
  ```

For more help, visit our [GitHub Discussions](https://github.com/axioma-ai-labs/nevron/discussions) or open an issue on the repository.