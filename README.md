# CPM - Context Protocol Manager

> The npm-inspired package manager for MCP servers

CPM is a Python-based package manager and runtime for Model Context Protocol (MCP) servers. Manage global and project-level MCP servers with dual-context configuration, just like npm.

⚠️ **STATUS: EARLY DEVELOPMENT** - Registry functionality is not yet released. The tool is currently not functional for package installation and management. Check back for updates.

## Quick Start

```bash
# Install CPM (development)
cd cpmanager
uv venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv pip install -e .

# Install an MCP server globally
cpm install brave-search

# Run it
cpm run brave-search

# Add to your client (Claude Desktop, Cursor, etc.)
cpm add brave-search --to claude
```

## Features

- 🌍 **Dual-Context Configuration** - Global (`~/.config/cpm/servers.json`) and project-level (`server.json`)
- 🔍 **Registry Integration** - Search and install servers from the MCP registry with caching
- 🎯 **Multi-Client Support** - Auto-detect and configure Claude Desktop, Cursor, Windsurf, VSCode, Cline, Continue, Goose
- 📦 **Group Management** - Organize servers with `@group` syntax for bulk operations
- 🚀 **Multiple Execution Modes** - Run servers in stdio (default), HTTP, or SSE mode
- 🔄 **Cross-Platform** - Windows, macOS, and Linux support

## Installation

### Development (From Source)

```bash
# Clone the repository
git clone https://github.com/shzbk/cpmanager.git
cd cpmanager

# Create and activate virtual environment
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install in editable mode
uv pip install -e .

# Verify installation
cpm --version
```

### Production (Coming Soon)

PyPI package and install script coming in future releases.

## Command Reference

### Server Management

```bash
# Install & manage servers
cpm install <name>                 # Install server globally
cpm install <name> --local         # Install to project (server.json)
cpm uninstall <name>               # Remove server
cpm ls                             # List installed servers
cpm search <query>                 # Search registry
cpm info <name>                    # Show server details
cpm update <name>                  # Update server
cpm outdated                       # Check for updates
```

### Running Servers

```bash
# Execute servers
cpm run <name>                     # Run in stdio mode (default)
cpm run <name> --http              # Run in HTTP mode
cpm run <name> --sse               # Run in SSE mode
cpm run @group                     # Run all servers in a group
cpm serve                          # Alias for 'cpm run --http'
```

### Group Management

```bash
# Organize with groups (@ prefix)
cpm group create @name             # Create new group
cpm group add @name <server>       # Add server to group
cpm group remove @name <server>    # Remove from group
cpm group list                     # List all groups
cpm group show @name               # Show servers in group
```

### Client Integration

```bash
# Manage client configurations
cpm add <name>                     # Add server to all detected clients
cpm add <name> --to claude         # Add to specific client
cpm remove <name>                  # Remove from clients
cpm sync                           # Sync to all clients
cpm reset <client>                 # Reset client config
cpm clients                        # Show supported clients
```

## Supported Clients

- Claude Desktop (Anthropic)
- Cursor
- Windsurf
- VSCode (with MCP extension)
- Cline
- Continue
- Goose

## Example Workflows

### 1. Global Server Installation

```bash
# Search for a server
cpm search "brave"

# Install it globally
cpm install brave-search

# Configure API key
export BRAVE_API_KEY="your-api-key"

# Test it
cpm run brave-search
```

### 2. Add to MCP Clients

```bash
# Install multiple servers
cpm install brave-search
cpm install filesystem

# Add to Claude Desktop (auto-detects)
cpm add brave-search
cpm add filesystem

# Or add to specific client
cpm add brave-search --to cursor
cpm add brave-search --to windsurf

# Restart your client - servers are ready!
```

### 3. Project-Level Setup

```bash
# Initialize project with servers
cpm init my-project
cd my-project

# Install project-specific servers
cpm install brave-search --local
cpm install filesystem --local

# Create groups for organization
cpm group create @research
cpm group add @research brave-search

# Run all research servers
cpm run @research --http
```

### 4. Group-Based Organization

```bash
# Create groups
cpm group create @database
cpm group create @ai-tools

# Add servers to groups
cpm group add @database mysql postgres
cpm group add @ai-tools brave-search embedding-model

# Run group as HTTP endpoint
cpm run @database --http
cpm run @ai-tools --http --port 8081
```

## Configuration

### Global Configuration

CPM stores global configuration in `~/.config/cpm/`:

- **`servers.json`** - Globally installed servers and groups
- **`cache/registry.json`** - Cached registry data (1 hour TTL)

### Project Configuration

CPM supports project-level `server.json` for project-specific servers:

- **`server.json`** - Project manifest (name, version, servers, devServers, groups)
- **`server-lock.json`** - Lock file with pinned versions and integrity hashes
- **`.cpm/`** - Local CPM directory with server configs

### Context Detection

CPM auto-detects context:
- If `server.json` exists in current directory → **local context**
- Otherwise → **global context** (`~/.config/cpm/`)
- Override with `--local` or `--global` flags

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/shzbk/cpmanager.git
cd cpmanager

# Create and activate virtual environment
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies and CPM in editable mode
uv pip install -e ".[dev]"

# Run tests
pytest

# Check code formatting
ruff format src/ tests/
ruff check src/ tests/
```

### Project Structure

```
cpmanager/
├── src/cpm/
│   ├── cli.py                      # Main CLI entry point (Click)
│   ├── core/
│   │   ├── config.py               # GlobalConfigManager
│   │   ├── local_config.py         # LocalConfigManager
│   │   ├── context.py              # ConfigContext (unified interface)
│   │   ├── schema.py               # Pydantic models
│   │   ├── registry.py             # RegistryClient
│   │   └── lockfile.py             # Lock file management
│   ├── clients/
│   │   ├── base.py                 # BaseClientManager interface
│   │   ├── registry.py             # ClientRegistry
│   │   └── managers/               # Platform-specific managers
│   │       ├── claude_desktop.py   # Claude Desktop
│   │       ├── cursor.py           # Cursor
│   │       ├── windsurf.py         # Windsurf
│   │       ├── vscode.py           # VSCode
│   │       ├── cline.py            # Cline
│   │       ├── continue_ext.py     # Continue
│   │       └── goose.py            # Goose
│   ├── commands/                   # ~25 CLI commands
│   ├── runtime/
│   │   └── executor.py             # ServerExecutor (FastMCP)
│   ├── ui/                         # TUI components
│   └── utils/                      # Shared utilities
├── tests/                          # Test suite
├── README.md                       # This file
├── LICENSE                         # MIT License
└── pyproject.toml                  # Project config
```

## License

MIT License - see [LICENSE](LICENSE) file for details.
