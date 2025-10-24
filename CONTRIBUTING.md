# Contributing to CPM

Thank you for considering contributing to CPM! This document provides guidelines for contributing.

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/cpm.git
   cd cpm
   ```

2. **Set up development environment**
   ```bash
   # Create virtual environment with uv
   uv venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows

   # Install in development mode
   uv pip install -e .

   # Install dev dependencies
   uv pip install pytest pytest-asyncio ruff
   ```

3. **Run tests**
   ```bash
   pytest
   ```

4. **Format code**
   ```bash
   ruff check src/ tests/
   ruff format src/ tests/
   ```

## Project Structure

```
cpm/
├── src/cpm/           # Main source code
│   ├── cli.py         # CLI entry point
│   ├── core/          # Core functionality
│   ├── commands/      # CLI commands
│   ├── clients/       # Client managers
│   ├── runtime/       # Server execution
│   └── utils/         # Utilities
├── tests/             # Test suite
└── pyproject.toml     # Project configuration
```

## Code Style

- Follow PEP 8
- Use type hints where possible
- Keep functions focused and small
- Write docstrings for public APIs
- Format with Ruff

## Testing

- Write tests for new features
- Ensure all tests pass before submitting PR
- Aim for good test coverage

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and formatting
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to your fork (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Commit Messages

Use clear, descriptive commit messages:
- `feat: add profile management commands`
- `fix: resolve server execution issue`
- `docs: update installation guide`
- `test: add tests for config manager`

## Questions?

Feel free to open an issue for questions or discussions!
