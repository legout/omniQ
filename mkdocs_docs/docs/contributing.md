# Contributing to OmniQ

We welcome contributions to OmniQ! Whether you're reporting an issue, submitting a feature request, or contributing code, your help is appreciated.

## Reporting Issues

If you encounter a bug or have a feature request, please submit an issue on our GitHub repository. When reporting a bug, please include:

- A clear and descriptive title.
- A detailed description of the issue, including steps to reproduce it.
- The version of OmniQ and Python you are using.
- Any relevant code snippets or error messages.

## Submitting Pull Requests

We are happy to accept pull requests. Please follow these steps to contribute code:

1. **Fork the repository** and create a new branch for your changes.
2. **Set up a development environment.** We recommend using a virtual environment:

```bash
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`

# Install dependencies
pip install -e ".[dev]"
```

3. **Make your changes.** Ensure your code follows the existing style and includes tests for any new functionality.
4. **Run the tests** to ensure everything is working correctly:

```bash
pytest
```

5. **Submit a pull request** with a clear description of your changes and why they are needed.

## Code Style

We use `black` for code formatting and `ruff` for linting. Please ensure your code conforms to these standards before submitting a pull request.

Thank you for contributing to OmniQ!