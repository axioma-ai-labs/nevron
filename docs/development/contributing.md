# Contributing Guide

Thank you for considering contributing to Nevron! This guide will help you get started with contributing to our project.

## Table of Contents
- [Ways to Contribute](#ways-to-contribute)
- [Development Process](#development-process)
- [Code Style and Standards](#code-style-and-standards)
- [Pull Request Guidelines](#pull-request-guidelines)
- [Getting Help](#getting-help)

## Ways to Contribute

1. **Code Contributions**
   - Bug fixes
   - New features
   - Performance improvements
   - Documentation improvements

2. **Non-Code Contributions**
   - Reporting bugs
   - Suggesting enhancements
   - Improving documentation
   - Answering questions in discussions

## Development Process

1. **Find or Create an Issue**
   - Check existing [issues](https://github.com/axioma-ai-labs/nevron/issues)
   - Look for `good first issue` or `help wanted` labels
   - If you want to work on something new, create an issue first to discuss it

2. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR-USERNAME/nevron.git
   cd nevron
   ```

3. **Create a Branch**
   - Create a new branch for your work:
    ```bash
    git checkout -b feature/issue-number-description
    # Example: feature/42-add-redis-cache
    ```
  - Use meaningful branch names, preferably referencing the issue number


4. **Make Changes**
   - Write your code
   - Follow the [project's coding standards](#code-style-and-standards)
   - Keep commits atomic and write meaningful commit messages
   - Test your changes thoroughly

5. **Test Your Changes**
   - Run formatting checks:
     ```bash
     make format
     ```
   - Run linting checks:
     ```bash
     make lint
     ```
   - Run tests:
     ```bash
     make test
     ```

6. **Push and Create PR**
   - Push your changes to your fork:
     ```bash
     git push origin feature/issue-number-description
     ```
   - Then create a Pull Request on GitHub.

## Code Style and Standards

### Python Standards
- Follow [PEP 8](https://peps.python.org/pep-0008/) style guide
- Follow [PEP 484](https://peps.python.org/pep-0484/) for type hints
- Follow [PEP 257](https://peps.python.org/pep-0257/) for docstrings
- Use Python 3.12+ features and patterns

### Naming Conventions
- Use descriptive names that reflect purpose
- Variables and functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_CASE_WITH_UNDERSCORES`
- Private attributes/methods: prefix with single underscore `_private_method`
- "Magic" methods: surrounded by double underscores `__str__`
- Type variable names: `PascalCase` preferably single letters (T, K, V)

### Code Organization
- One class per file unless classes are closely related
- Group related functionality into modules
- Use absolute imports
- Order imports as: standard library, third-party, local
- Use `isort` for import sorting
- Maximum line length: 100 characters
- Use 4 spaces for indentation (no tabs)

### Documentation
- All public APIs must have docstrings
- Use Google-style docstring format:
  ```python
  def function_name(param1: str, param2: int) -> bool:
      """Short description of function.

      Longer description if needed.

      Args:
          param1: Description of param1
          param2: Description of param2

      Returns:
          Description of return value

      Raises:
          ValueError: Description of when this error occurs
      """
  ```
- Include type hints for all function arguments and return values
- Document exceptions that may be raised
- Keep comments focused on why, not what
- Update documentation when changing code

### Code Quality
- Keep functions small and focused (preferably under 50 lines)
- Maximum function arguments: 5
- Use early returns to reduce nesting
- Avoid global variables
- Use constants instead of magic numbers
- Handle all possible exceptions appropriately
- Use context managers (`with` statements) for resource management
- Use f-strings for string formatting
- Use list/dict/set comprehensions when they improve readability

### Testing Standards
- Write tests for all new code
- Maintain minimum 90% test coverage
- Follow Arrange-Act-Assert pattern
- Use meaningful test names that describe the scenario
- One assertion per test when possible
- Use pytest fixtures for common setup
- Mock external dependencies
- Test edge cases and error conditions

### Performance Considerations
- Use appropriate data structures
- Avoid unnecessary object creation
- Use generators for large datasets
- Profile code when performance is critical
- Consider memory usage
- Use `collections` module specialized containers when appropriate

### Security Best Practices
- Never commit sensitive data (API keys, passwords)
- Use environment variables for configuration
- Validate all input data
- Use secure defaults
- Follow OWASP security guidelines
- Use `secrets` module for cryptographic operations

### Version Control
- Write meaningful commit messages
- One logical change per commit
- Reference issue numbers in commits
- Keep commits small and focused
- Rebase feature branches on main before PR

## Pull Request Guidelines

### PR Title Format
Title should be concise and descriptive.

### PR Description Should Include
- Reference to related issue(s)
- Clear description of changes
- Breaking changes (if any)

### Review Process
1. Automated checks must pass
2. At least one maintainer approval required
3. All review comments must be resolved
4. Documentation must be updated

### Merging
- Always squash commits before merging
- Merge into `dev` branch first
- Once `dev` is stable, merge into `main` (done by maintainers)

## Getting Help

- Join our [Discussions](https://github.com/axioma-ai-labs/nevron/discussions)
- Ask questions in issue comments
- Tag maintainers if stuck

Remember: No contribution is too small, and all contributions are valued! 