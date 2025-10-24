# Getting Started with CPM

## Installation

```bash
# Clone the repository
git clone https://github.com/shzbk/cpmanager.git
cd cpmanager

# Create virtual environment
uv venv

# Activate it
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install CPM in development mode
uv pip install -e .
```

## Quick Start

```bash
# Test the CLI
cpm --version
cpm --help

# Search for MCP servers
cpm search "brave"

# List installed servers (global)
cpm ls

# Install a server globally
cpm install brave-search

# Run it
cpm run brave-search

# Add to Claude Desktop
cpm add brave-search --to claude
```

## Testing

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run all tests
pytest

# Run specific test file
pytest tests/test_config.py

# Run with coverage
pytest --cov=src/cpm tests/
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

## Code Quality

```bash
# Format code with ruff
ruff format src/ tests/

# Check for linting issues
ruff check --fix src/ tests/

# Run all checks
pytest && ruff check src/ tests/
```

## Project Structure

- `src/cpm/` - Main package
  - `core/` - Configuration and registry management
  - `clients/` - MCP client integrations
  - `commands/` - CLI command implementations
  - `runtime/` - Server execution
  - `utils/` - Shared utilities
- `tests/` - Test suite

## Key Concepts

**Global vs Local Context:**
- Global: `~/.config/cpm/servers.json` - available everywhere
- Local: `./server.json` - project-specific (auto-detected)

**Groups (@syntax):**
```bash
cpm group create @database
cpm group add @database mysql postgres
cpm run @database --http
```

**Client Integration:**
```bash
cpm add server-name --to claude      # Add to Claude Desktop
cpm sync                              # Sync all servers to clients
```

## Resources

- **MCP Specification**: https://modelcontextprotocol.io/
- **FastMCP**: https://github.com/jlowin/fastmcp
- **GitHub Repository**: https://github.com/shzbk/cpmanager

## Troubleshooting

**Command not found after install:**
```bash
# Make sure virtual environment is activated
source .venv/bin/activate
uv pip install -e .
```

**Tests failing:**
```bash
# Ensure dev dependencies are installed
uv pip install -e ".[dev]"
pytest -v  # Run with verbose output
```

**Registry connection issues:**
Check that registry URL is accessible (default: localhost:8000)
