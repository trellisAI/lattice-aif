# Contributing to Lattice AIF

Thank you for your interest in contributing to Lattice AIF! We welcome all contributions, including bug reports, feature requests, documentation improvements, and code changes.

## How to Contribute

### Reporting Bugs

- Search the [GitHub Issues](https://github.com/trellisAI/lattice-aif/issues) to see if the bug has already been reported.
- If not, create a new issue. Include a clear and descriptive title, steps to reproduce the bug, the expected behavior, and any relevant logs or screenshots.

### Suggesting Features

- We're always looking for new ideas! If you have a feature request, please open a new issue and describe the functionality you'd like to see, along with use cases.

### Submitting Pull Requests

1. **Fork the repository** and create a new branch for your changes.
2. **Implement your changes**. Make sure to follow the existing coding style and include tests if applicable.
3. **Run tests** to ensure your changes didn't break anything.
4. **Submit a pull request**. Provide a clear description of your changes and why they are needed.

## Development Environment Setup

### Prerequisites

- Python 3.8+
- `pip`

### Initializing the Workspace

```bash
# Clone the repository
git clone https://github.com/trellisAI/lattice-aif.git
cd lattice-aif

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install core development dependencies
pip install -e "./lattice-engine"
pip install -e "./lattice-client"
pip install -e "./lattice-server"
```

## Coding Standards

- **Style**: We use `black` for code formatting and `ruff` for linting.
- **Documentation**: All new features and public API changes should include updated documentation.
- **Commit Messages**: Use clear and concise commit messages that describe the changes.

## Framework Architecture

Lattice AIF is divided into three core packages:

- **`lattice-engine`**: The central daemon and orchestration layer.
- **`lattice-client`**: The CLI and UI management interface.
- **`lattice-server`**: A lightweight utility for tool registration.

Please follow the architecture and design patterns established in each package.

## License

By contributing to Lattice AIF, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).
