# CPM - Context Protocol Manager

> The npm for MCP servers

CPM is a streamlined package manager and runtime for Model Context Protocol (MCP) servers. Install, manage, and run MCP servers with the simplicity developers expect from npm.

## Quick Start

```bash
# Install CPM
curl -sSL https://cpm.dev/install | bash

# Install an MCP server
cpm install brave-search

# Run it
cpm run brave-search

# Add to your client (Claude Desktop, Cursor, etc.)
cpm client add claude-desktop brave-search
```

## Features

- 🚀 **Simple Installation** - Install servers from the registry with one command
- 🔍 **Easy Discovery** - Search and explore available MCP servers
- 🎯 **Client Integration** - Auto-detect and configure all major MCP clients
- 📦 **Profile Management** - Organize servers into reusable profiles
- 🌐 **Multiple Modes** - Run servers in stdio, HTTP, or SSE mode
- 🔄 **Cross-Platform** - Works on Windows, macOS, and Linux

## Installation

### Recommended: Install Script

```bash
curl -sSL https://cpm.dev/install | bash
```

### Using uv

```bash
uv tool install cpm
```

### Using pipx

```bash
pipx install cpm
```

## Command Reference

### Core Commands

```bash
# Install & manage servers
cpm install <server-name>          # Install from registry
cpm uninstall <server-name>        # Remove server
cpm ls                             # List installed servers
cpm search <query>                 # Search registry
cpm info <server-name>             # Show server details

# Run servers
cpm run <server-name>              # Run in stdio mode (default)
cpm run <server-name> --http       # Run in HTTP mode
cpm run <server-name> --sse        # Run in SSE mode
```

### Profile Management

```bash
# Create and manage profiles
cpm profile create <name>              # Create new profile
cpm profile add <profile> <server>     # Add server to profile
cpm profile remove <profile> <server>  # Remove server from profile
cpm profile list                       # List all profiles

# Run profiles
cpm profile run <name>                 # Run all servers in profile
cpm profile run <name> --http          # Aggregate as HTTP endpoint
```

### Client Integration

```bash
# Manage client configurations
cpm client list                        # Show all supported clients
cpm client detect                      # Detect installed clients
cpm client add <client> <server>       # Add server to client config
cpm client remove <client> <server>    # Remove from client config
cpm client sync <client>               # Sync all servers to client
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

### 1. Basic Server Installation

```bash
# Search for a server
cpm search "web search"

# Install it
cpm install brave-search

# Configure API key
export BRAVE_API_KEY="your-key"

# Run it
cpm run brave-search
```

### 2. Client Integration

```bash
# Install multiple servers
cpm install brave-search
cpm install filesystem

# Add them to Claude Desktop
cpm client add claude-desktop brave-search
cpm client add claude-desktop filesystem

# Restart Claude Desktop - servers are ready!
```

### 3. Profile-Based Organization

```bash
# Create a web development profile
cpm profile create web-dev

# Add relevant servers
cpm profile add web-dev brave-search
cpm profile add web-dev fetch
cpm profile add web-dev filesystem

# Run all servers as one HTTP endpoint
cpm profile run web-dev --http --port 8080
```

## Configuration

CPM stores configuration in `~/.config/cpm/`:

- `servers.json` - Installed servers and profiles
- `cache/` - Registry cache

## Development

### Setup

```bash
git clone https://github.com/yourusername/cpm.git
cd cpm

# Create virtual environment
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install in development mode
uv pip install -e .

# Run tests
pytest
```

### Project Structure

```
cpm/
├── src/cpm/
│   ├── cli.py              # Main CLI entry point
│   ├── core/               # Core logic (config, schema, registry)
│   ├── clients/            # Client managers
│   ├── runtime/            # Server execution
│   ├── commands/           # CLI commands
│   └── utils/              # Utilities
├── tests/                  # Test suite
└── pyproject.toml          # Project configuration
```

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details.

## License

MIT License - see [LICENSE](LICENSE) file for details.
