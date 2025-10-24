# Getting Started with CPM

## Installation

```bash
cd cpm
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install in development mode
uv pip install -e .
```

## Quick Test

```bash
# Test the CLI
cpm --version
cpm --help

# Search for servers
cpm search

# List installed servers (will be empty initially)
cpm ls
```

## Testing

```bash
# Install dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# Try the CLI
cpm --help
cpm search
```

## Architecture Overview

```
User
  ↓
CLI (cpm)
  ↓
Commands (install, run, etc.)
  ↓
Core (GlobalConfigManager, RegistryClient)
  ↓
Runtime (ServerExecutor with FastMCP)
  ↓
MCP Server Process
```

## Development Commands

```bash
# Format code
ruff format src/ tests/

# Check code
ruff check src/ tests/

# Run tests
pytest

# Run specific test
pytest tests/test_config.py

# Install in development mode
uv pip install -e .
```

## Resources

- **FastMCP Docs**: https://github.com/jlowin/fastmcp
- **MCP Spec**: https://modelcontextprotocol.io/
- **CONTRIBUTING**: See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines

## Next Steps

- Read [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines
- Check the issue tracker for open tasks
- Review ARCHITECTURE.md for code organization
