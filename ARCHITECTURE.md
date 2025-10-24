# CPM v2.0 - Architecture & Project Structure

## 📁 Project Directory Structure

```
cpm/
├── src/cpm/                          # Source code
│   ├── __init__.py                   # Version exports
│   ├── cli.py                        # Main CLI entry point
│   │
│   ├── core/                         # Core business logic
│   │   ├── __init__.py
│   │   ├── config.py                 # GlobalConfigManager
│   │   ├── local_config.py           # LocalConfigManager (NEW)
│   │   ├── context.py                # ConfigContext (NEW - unified interface)
│   │   ├── schema.py                 # Pydantic models
│   │   ├── registry.py               # RegistryClient
│   │   └── lockfile.py               # LockfileManager (NEW)
│   │
│   ├── clients/                      # MCP client integrations
│   │   ├── __init__.py
│   │   ├── base.py                   # BaseClientManager, JSON/YAML managers
│   │   ├── registry.py               # ClientRegistry
│   │   └── managers/                 # Platform-specific implementations
│   │       ├── __init__.py
│   │       ├── claude_desktop.py
│   │       ├── cursor.py
│   │       ├── windsurf.py
│   │       ├── vscode.py
│   │       ├── cline.py
│   │       ├── continue_ext.py
│   │       └── goose.py
│   │
│   ├── runtime/                      # Server execution
│   │   ├── __init__.py
│   │   └── executor.py               # ServerExecutor (FastMCP)
│   │
│   ├── commands/                     # CLI command implementations
│   │   ├── __init__.py
│   │   │
│   │   ├── install.py                # MODIFIED: add --local, --save-dev
│   │   ├── uninstall.py              # MODIFIED: add --purge
│   │   ├── config.py                 # MODIFIED: add --local
│   │   ├── ls.py                     # MODIFIED: add --local, --all
│   │   ├── info.py                   # Keep as-is
│   │   ├── search.py                 # Keep as-is
│   │   ├── run.py                    # MODIFIED: add --local, @group support
│   │   ├── serve.py                  # NEW: alias for run --http
│   │   │
│   │   ├── add.py                    # NEW: smart client add
│   │   ├── remove.py                 # NEW: smart client remove
│   │   ├── sync.py                   # NEW: client sync
│   │   ├── reset.py                  # NEW: client reset
│   │   │
│   │   ├── clients.py                # NEW: client management (ls, detect, show)
│   │   ├── group.py                  # RENAMED from profile.py, add @ support
│   │   │
│   │   ├── init.py                   # NEW: project initialization
│   │   ├── update.py                 # NEW: update servers
│   │   ├── outdated.py               # NEW: check versions
│   │   ├── link.py                   # NEW: link local server
│   │   ├── unlink.py                 # NEW: unlink local server
│   │   │
│   │   ├── publish.py                # Keep, enhance
│   │   ├── validate.py               # Keep, enhance
│   │   ├── login.py                  # NEW: registry auth
│   │   ├── logout.py                 # NEW: registry logout
│   │   ├── whoami.py                 # NEW: show current user
│   │   │
│   │   ├── doctor.py                 # Keep, enhance
│   │   ├── cache.py                  # NEW: cache management
│   │   ├── settings.py               # NEW: CPM settings
│   │   └── upgrade.py                # NEW: update CPM itself
│   │
│   ├── ui/                           # User interface components
│   │   ├── __init__.py
│   │   ├── config_tui.py             # Interactive config (keep, fix bugs)
│   │   └── prompts.py                # NEW: questionary-based prompts
│   │
│   └── utils/                        # Shared utilities
│       ├── __init__.py
│       ├── display.py                # Rich console helpers
│       ├── logging.py                # Logging configuration
│       ├── validators.py             # NEW: validation utilities
│       └── semver.py                 # NEW: semver parsing
│
├── tests/                            # Test suite
│   ├── __init__.py
│   ├── conftest.py                   # Pytest fixtures
│   ├── test_core/                    # Core module tests
│   │   ├── test_config.py
│   │   ├── test_local_config.py      # NEW
│   │   ├── test_context.py           # NEW
│   │   ├── test_schema.py
│   │   ├── test_registry.py
│   │   └── test_lockfile.py          # NEW
│   ├── test_clients/                 # Client tests
│   ├── test_runtime/                 # Runtime tests
│   ├── test_commands/                # Command tests
│   └── test_integration/             # Integration tests
│
├── docs/                             # Documentation
│   ├── index.md                      # Main documentation
│   ├── commands.md                   # Command reference
│   ├── api.md                        # SDK/API reference
│   ├── contributing.md               # Contribution guide
│   └── migration.md                  # v1 → v2 migration guide
│
├── examples/                         # Example projects
│   ├── basic/                        # Basic usage
│   ├── ai-agent/                     # AI agent project
│   └── server-dev/                   # Server development
│
├── scripts/                          # Development scripts
│   ├── setup.sh                      # Setup environment
│   ├── test.sh                       # Run tests
│   └── build.sh                      # Build package
│
├── pyproject.toml                    # Project metadata
├── README.md                         # User-facing docs
├── ARCHITECTURE.md                   # This file
├── COMMANDS.md                       # Command map (NEW)
├── Plan.md                           # Design specification
├── .gitignore
├── .python-version
└── LICENSE
```

---

## 🎯 Key Design Patterns

### 1. **Context Pattern** (NEW)
```python
# Unified interface for global vs local context
from cpm.core.context import ConfigContext

# Auto-detects context
config = ConfigContext()  # Checks for cpm.json

# Explicit context
config = ConfigContext(local=True)   # Force local
config = ConfigContext(local=False)  # Force global

# All methods work the same
config.manager.add_server(server)
config.manager.list_servers()
```

### 2. **Command Pattern**
```python
# All commands follow the same structure
@click.command()
@click.argument('servers', nargs=-1)
@click.option('--local', is_flag=True)
@click.pass_context
def command(ctx, servers, local):
    """Command description"""
    config = ConfigContext(local=local or ctx.obj.get('local'))
    # Command logic
```

### 3. **@ Group Syntax**
```python
# Groups referenced with @ everywhere
def parse_argument(arg: str):
    """Parse server or group reference"""
    if arg.startswith('@'):
        # It's a group
        group_name = arg[1:]
        return ('group', group_name)
    else:
        # It's a server
        return ('server', arg)
```

### 4. **Registry Pattern**
```python
# Centralized client registry
from cpm.clients.registry import ClientRegistry

registry = ClientRegistry()
detected = registry.detect_installed_clients()
manager = registry.get_client_manager('cursor')
```

---

## 📦 Core Data Models

### ServerConfig (Pydantic)
```python
from pydantic import BaseModel
from typing import List, Dict, Optional

class STDIOServerConfig(BaseModel):
    name: str
    command: str
    args: List[str] = []
    env: Dict[str, str] = {}
    groups: List[str] = []           # Group membership
    version: Optional[str] = None    # NEW: version tracking

class RemoteServerConfig(BaseModel):
    name: str
    url: str
    headers: Dict[str, str] = {}
    groups: List[str] = []
    version: Optional[str] = None

ServerConfig = STDIOServerConfig | RemoteServerConfig
```

### Local Manifest (cpm.json)
```python
class LocalManifest(BaseModel):
    name: str
    version: str
    servers: Dict[str, str]          # name → version
    devServers: Dict[str, str] = {}  # dev dependencies
    groups: Dict[str, List[str]] = {}  # group → servers
    config: Dict[str, Dict[str, str]] = {}  # server → env vars
```

### Lockfile (cpm-lock.json)
```python
class ServerLock(BaseModel):
    version: str
    resolved: str                     # Registry URL
    integrity: str                    # SHA512 hash
    installation: Dict               # Installation config

class Lockfile(BaseModel):
    lockfileVersion: int = 1
    servers: Dict[str, ServerLock]
```

---

## 🔄 Data Flow

### Install Flow (Global)
```
User: cpm install mysql
    ↓
install.py → ConfigContext(global)
    ↓
RegistryClient.get_server('mysql')
    ↓
GlobalConfigManager.add_server(server)
    ↓
Write to ~/.cpm/servers.json
```

### Install Flow (Local)
```
User: cpm install mysql --local
    ↓
install.py → ConfigContext(local)
    ↓
RegistryClient.get_server('mysql')
    ↓
LocalConfigManager.add_server(server)
    ↓
Write to cpm.json + cpm-lock.json
```

### Add Flow (Client Integration)
```
User: cpm add mysql
    ↓
add.py → parse arguments
    ↓
ClientRegistry.detect_installed_clients()
    ↓
For each client:
    ClientManager.add_server(mysql)
    ↓
    Write to client config
```

### Run Flow (@group support)
```
User: cpm run @database --http
    ↓
run.py → parse_argument('@database')
    ↓
ConfigContext.get_servers_in_group('database')
    ↓
ServerExecutor.aggregate(servers, mode='http')
    ↓
FastMCP starts aggregated server
```

---

## 🏗️ Migration Strategy

### Phase 1: Core Extensions (Week 1)
**Files to create:**
- `src/cpm/core/local_config.py`
- `src/cpm/core/context.py`
- `src/cpm/core/lockfile.py`
- `tests/test_core/test_local_config.py`
- `tests/test_core/test_context.py`

**Files to modify:**
- `src/cpm/core/config.py` - Add version tracking
- `src/cpm/core/schema.py` - Add version fields

### Phase 2: Command Refactor (Week 2)
**Files to create:**
- `src/cpm/commands/add.py`
- `src/cpm/commands/remove.py`
- `src/cpm/commands/sync.py`
- `src/cpm/commands/reset.py`
- `src/cpm/commands/clients.py`
- `src/cpm/commands/serve.py`
- `src/cpm/commands/init.py`
- `src/cpm/commands/update.py`
- `src/cpm/commands/outdated.py`
- `src/cpm/commands/link.py`
- `src/cpm/commands/unlink.py`
- `src/cpm/commands/cache.py`
- `src/cpm/commands/settings.py`
- `src/cpm/commands/upgrade.py`

**Files to modify:**
- `src/cpm/cli.py` - Restructure command registration
- `src/cpm/commands/install.py` - Add --local, --save-dev
- `src/cpm/commands/uninstall.py` - Add --purge
- `src/cpm/commands/config.py` - Add --local
- `src/cpm/commands/ls.py` - Add --local, --all
- `src/cpm/commands/run.py` - Add @group support
- `src/cpm/commands/group.py` - Rename from profile.py

### Phase 3: Polish & Testing (Week 3)
**Focus areas:**
- Integration tests for all workflows
- Documentation updates
- Migration guide
- Performance optimization

---

## 🎨 Code Style Guidelines

### Imports
```python
# Standard library
import json
from pathlib import Path
from typing import Dict, List, Optional

# Third-party
import click
from rich.console import Console
from pydantic import BaseModel

# Local
from cpm.core import ConfigContext
from cpm.clients import ClientRegistry
```

### Error Handling
```python
from rich.console import Console
console = Console(stderr=True)

try:
    # Operation
    config.add_server(server)
except ServerExistsError as e:
    console.print(f"[yellow]Warning: {e}[/]")
    if not force:
        raise
except Exception as e:
    console.print(f"[red]Error: {e}[/]")
    if verbose:
        console.print_exception()
    raise click.Abort()
```

### Logging
```python
import logging
logger = logging.getLogger(__name__)

# Debug info
logger.debug(f"Adding server {server.name} to context")

# User-facing messages via Rich
console.print(f"[green]✓[/] Added {server.name}")
```

---

## 🧪 Testing Strategy

### Unit Tests
```python
# tests/test_core/test_context.py
def test_context_auto_detection(tmp_path):
    """Test context auto-detection"""
    # Create cpm.json
    manifest = tmp_path / "cpm.json"
    manifest.write_text('{"name": "test", "servers": {}}')

    # Change to directory
    os.chdir(tmp_path)

    # Should detect local context
    ctx = ConfigContext()
    assert ctx.context == "local"
```

### Integration Tests
```python
# tests/test_integration/test_workflows.py
def test_local_install_workflow(tmp_path, cli_runner):
    """Test complete local install workflow"""
    result = cli_runner.invoke(cli, ['init', '--yes'], cwd=tmp_path)
    assert result.exit_code == 0

    result = cli_runner.invoke(cli, ['install', 'mysql', '--local'], cwd=tmp_path)
    assert result.exit_code == 0

    # Check cpm.json
    manifest = json.loads((tmp_path / 'cpm.json').read_text())
    assert 'mysql' in manifest['servers']
```

---

## 📚 Documentation Structure

### User Documentation
- **README.md** - Quick start, installation, basic usage
- **docs/commands.md** - Complete command reference
- **docs/examples/** - Real-world examples

### Developer Documentation
- **ARCHITECTURE.md** - This file (architecture overview)
- **COMMANDS.md** - Command implementation map
- **CONTRIBUTING.md** - Contribution guidelines
- **docs/api.md** - Python/SDK API reference

---

## 🚀 Build & Release Process

### Local Development
```bash
# Setup
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate
pip install -e ".[dev]"

# Run tests
pytest tests/

# Format code
ruff format src/ tests/
ruff check --fix src/ tests/

# Run CPM locally
cpm --help
```

### Release Process
```bash
# Update version in src/cpm/__init__.py
__version__ = "2.0.0"

# Build
python -m build

# Publish to PyPI
python -m twine upload dist/*

# Create GitHub release
gh release create v2.0.0 --title "v2.0.0" --notes "Release notes"
```

---

This architecture supports the complete v2.0 vision while maintaining clean code organization and easy extensibility.
