# Nevron - Autonomous Agent
[![CI](https://github.com/axioma-ai-labs/aa-core/actions/workflows/main.yml/badge.svg)](https://github.com/axioma-ai-labs/aa-core/actions/workflows/main.yml)
[![codecov](https://codecov.io/gh/axioma-ai-labs/nevron/branch/main/graph/badge.svg?token=krO46pgB7P)](https://codecov.io/gh/axioma-ai-labs/nevron)
[![Build Docker image](https://github.com/axioma-ai-labs/nevron/actions/workflows/docker.yml/badge.svg)](https://github.com/axioma-ai-labs/nevron/actions/workflows/docker.yml)
[![Docs](https://img.shields.io/badge/Nevron-Docs-blue)](https://axioma-ai-labs.github.io/nevron/)

## Overview

This is a simple autonomous agent which can perform various tasks on its own.

Description of the agent in bullet points:

- This autonomous agent is designed to perform the tasks on his own. 
- The core of the agent is implemented by planning, feedback and memory modules. 
- The real intelligence is powered by LLMs. Currently we support OpenAI and Anthropic.
- The actions of the agent are defined in workflows, which encapsulate logic of performing the task.
- Different 3rd party services are integrated with the agent via tools, which are used in the workflows. Example of the tools:
  - Telegram
  - Twitter
  - Perplexity for research
  - Some API for getting news (to be customized)

## TLDR: Start the agent

1. Install pipenv if you haven't already:
```bash
pip install pipenv
```

2. Install dependencies:
```bash
make deps
```

3. Copy and configure environment variables:
```bash
cp .env.dev .env
```

> [!NOTE]
> You must configure the environment variables before running the agent!

4. Run the agent:
```bash
make run
```

## Documentation

You can find the documentation in the [docs](docs) folder, as well as on the official Nevron Docs website.

## Contributing

Contributions are welcome! Please follow the [CONTRIBUTING](CONTRIBUTING.md) file for more information.

## Security

For security-related matters, please review our [Security Policy](SECURITY.md).

## License

This project is licensed under the Nevron Public License (NPL). See the [LICENSE](LICENSE) file for details.

---

Made with ❤️ by [Neurobro](https://neurobro.ai)
