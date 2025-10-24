# CPM v2.0 - Command Implementation Map

This document maps every CLI command to its implementation file and key functions. Use this to understand and navigate the codebase.

---

## 📋 Command Structure Overview

```
All commands follow: cpm <verb> <subject> [options]

Entry Point: src/cpm/cli.py → main() function
Each command: src/cpm/commands/<command>.py
```

---

## 🗺️ Complete Command Map

### A. SERVER LIFECYCLE

#### `cpm install`
**File:** `src/cpm/commands/install.py`
**Function:** `install(servers, local, save_dev, version, ...)`
**Key Logic:**
- Detects context (global vs local)
- Fetches server metadata from registry
- Installs to appropriate location
- Creates/updates lockfile if local

**Options:**
- `--local` → Add to cpm.json
- `--save-dev` → Add to devServers
- `--version` → Specific version
- `--frozen-lockfile` → Use exact versions

**Dependencies:**
- `ConfigContext` → Context detection
- `RegistryClient` → Fetch metadata
- `GlobalConfigManager` or `LocalConfigManager`

---

#### `cpm uninstall`
**File:** `src/cpm/commands/uninstall.py`
**Function:** `uninstall(servers, local, purge, ...)`
**Key Logic:**
- Removes from servers.json or cpm.json
- If `--purge`, also removes from all clients
- Updates lockfile if local

**Options:**
- `--local` → Remove from cpm.json
- `--purge` → Also remove from clients

**Dependencies:**
- `ConfigContext`
- `ClientRegistry` (if --purge)

---

#### `cpm config`
**File:** `src/cpm/commands/config.py`
**Function:** `config(server, key_values, set_flag, view, edit, reset, local, ...)`
**Key Logic:**
- Opens interactive TUI by default
- Supports programmatic `--set KEY=VALUE`
- Editor mode with `--edit`
- Context-aware (global vs local)

**Options:**
- `--set KEY=VALUE` → Set specific value
- `--view` → Show current config
- `--edit` → Open in $EDITOR
- `--reset` → Reset to defaults
- `--local` → Configure for project

**Dependencies:**
- `ConfigContext`
- `config_tui.py` → Interactive UI

---

#### `cpm ls`
**File:** `src/cpm/commands/ls.py`
**Function:** `ls(local, all, long, json, tree, clients, ...)`
**Key Logic:**
- Lists installed servers
- Multiple output formats
- Can show client assignments

**Options:**
- `--local` → List from cpm.json
- `--all` → Both global + local
- `--long` → Detailed view
- `--json` → JSON output
- `--tree` → Show dependencies
- `--clients` → Show client assignments

**Dependencies:**
- `ConfigContext`
- `ClientRegistry` (if --clients)

---

#### `cpm info`
**File:** `src/cpm/commands/info.py`
**Function:** `info(server, tools, resources, prompts, ...)`
**Key Logic:**
- Fetches server metadata from registry
- Shows tools/resources/prompts

**Options:**
- `--tools` → List tools only
- `--resources` → List resources only
- `--prompts` → List prompts only

**Dependencies:**
- `RegistryClient`

---

#### `cpm search`
**File:** `src/cpm/commands/search.py`
**Function:** `search(query, category, tag, ...)`
**Key Logic:**
- Searches registry with filters
- Pretty-prints results

**Options:**
- `--category` → Filter by category
- `--tag` → Filter by tag

**Dependencies:**
- `RegistryClient`

---

#### `cpm run`
**File:** `src/cpm/commands/run.py`
**Function:** `run(target, http, port, host, local, ...)`
**Key Logic:**
- Parses target (server or @group)
- Starts server(s) via FastMCP
- Supports stdio/HTTP/SSE modes

**Target Parsing:**
```python
def parse_target(target):
    if target.startswith('@'):
        # Group reference
        group_name = target[1:]
        servers = config.get_servers_in_group(group_name)
        return ('group', servers)
    else:
        # Server reference
        server = config.get_server(target)
        return ('server', server)
```

**Options:**
- `--http` → Run as HTTP server
- `--port` → Custom port
- `--host` → Bind address
- `--local` → Use local config

**Dependencies:**
- `ConfigContext`
- `ServerExecutor` → FastMCP wrapper

---

#### `cpm serve`
**File:** `src/cpm/commands/serve.py`
**Function:** `serve(target, port, ...)`
**Key Logic:**
- Alias for `run --http`
- Convenient shortcut

**Options:**
- `-p, --port` → Custom port

**Implementation:**
```python
@click.command()
@click.argument('target')
@click.option('-p', '--port', default=6276)
def serve(target, port):
    """Serve server/group as HTTP (alias for run --http)"""
    # Call run command with http=True
    ctx = click.get_current_context()
    ctx.invoke(run, target=target, http=True, port=port)
```

---

### B. CLIENT OPERATIONS

#### `cpm add`
**File:** `src/cpm/commands/add.py`
**Function:** `add(targets, to, ...)`
**Key Logic:**
- Parses targets (servers or @groups)
- Detects installed clients
- Adds to specified or ALL clients

**Target Parsing:**
```python
def parse_targets(targets):
    """Parse mix of servers and @groups"""
    servers = []
    for target in targets:
        if target.startswith('@'):
            # Expand group
            group_servers = config.get_servers_in_group(target[1:])
            servers.extend(group_servers)
        else:
            servers.append(config.get_server(target))
    return servers
```

**Options:**
- `--to <client>` → Target specific client(s)
- `--to all` → Explicit all clients

**Dependencies:**
- `ConfigContext`
- `ClientRegistry`

---

#### `cpm remove`
**File:** `src/cpm/commands/remove.py`
**Function:** `remove(targets, from_clients, ...)`
**Key Logic:**
- Removes from client configs (NOT uninstall)
- Supports @groups
- Default: removes from ALL clients

**Options:**
- `--from <client>` → Target specific client
- `--from all` → Explicit all clients

**Dependencies:**
- `ConfigContext`
- `ClientRegistry`

---

#### `cpm sync`
**File:** `src/cpm/commands/sync.py`
**Function:** `sync(servers, to, group, ...)`
**Key Logic:**
- Synchronizes servers to clients
- Can sync all or specific servers/groups
- Updates client configs

**Options:**
- `--to <client>` → Target client
- `--to all` → All clients

**Dependencies:**
- `ConfigContext`
- `ClientRegistry`

---

#### `cpm reset`
**File:** `src/cpm/commands/reset.py`
**Function:** `reset(from_clients, yes, ...)`
**Key Logic:**
- Clears client configurations
- Requires confirmation unless `-y`

**Options:**
- `--from <client>` → Target client
- `--from all` → All clients
- `-y, --yes` → Skip confirmation

**Dependencies:**
- `ClientRegistry`

---

#### `cpm clients`
**File:** `src/cpm/commands/clients.py`
**Subcommands:**
- `ls` → List supported clients
- `detect` → Detect installed clients
- `show <client>` → Show client details

**Functions:**
- `clients_ls()` → List all supported
- `clients_detect()` → Detect installed
- `clients_show(client)` → Show details

**Dependencies:**
- `ClientRegistry`

---

### C. GROUP OPERATIONS

#### `cpm group`
**File:** `src/cpm/commands/group.py`
**Subcommands:**
- `create <name>` → Create group
- `delete <name>` → Delete group
- `rename <old> <new>` → Rename group
- `add <group> <servers...>` → Add servers to group
- `remove <group> <servers...>` → Remove from group
- `ls` → List all groups
- `show <name>` → Show group details

**Functions:**
- `group_create(name, description)`
- `group_delete(name)`
- `group_rename(old, new)`
- `group_add(group, servers)`
- `group_remove(group, servers)`
- `group_ls()`
- `group_show(name)`

**Dependencies:**
- `ConfigContext`

---

### D. DEVELOPER COMMANDS

#### `cpm init`
**File:** `src/cpm/commands/init.py`
**Function:** `init(yes, template, ...)`
**Key Logic:**
- Creates cpm.json in current directory
- Interactive wizard or --yes for defaults
- Supports templates (ai-agent, etc.)

**Creates:**
- `cpm.json` → Manifest
- `.cpm/` → Local config directory

**Options:**
- `--yes` → Use defaults
- `--template <name>` → Use template

**Dependencies:**
- `LocalConfigManager`
- `prompts.py` → Interactive prompts

---

#### `cpm update`
**File:** `src/cpm/commands/update.py`
**Function:** `update(servers, latest, ...)`
**Key Logic:**
- Updates servers to newer versions
- Respects semver ranges
- Updates lockfile

**Options:**
- `--latest` → Upgrade to latest (ignore semver)

**Dependencies:**
- `ConfigContext`
- `RegistryClient`
- `semver.py` → Version parsing

---

#### `cpm outdated`
**File:** `src/cpm/commands/outdated.py`
**Function:** `outdated(json_output, ...)`
**Key Logic:**
- Checks for outdated servers
- Compares current vs latest versions

**Options:**
- `--json` → JSON output

**Dependencies:**
- `ConfigContext`
- `RegistryClient`

---

#### `cpm link`
**File:** `src/cpm/commands/link.py`
**Function:** `link(server, ...)`
**Key Logic:**
- Links local server for development
- Makes server available globally

**Usage:**
```bash
# In server directory
cd my-server
cpm link  # No args, uses current directory

# In project directory
cd my-project
cpm link my-server  # Links specific server
```

**Dependencies:**
- `GlobalConfigManager`
- `LocalConfigManager`

---

#### `cpm unlink`
**File:** `src/cpm/commands/unlink.py`
**Function:** `unlink(server, ...)`
**Key Logic:**
- Unlinks local server
- Restores registry version

**Dependencies:**
- `GlobalConfigManager`

---

### E. PUBLISHING COMMANDS

#### `cpm publish`
**File:** `src/cpm/commands/publish.py`
**Function:** `publish(tag, access, dry_run, ...)`
**Key Logic:**
- Validates manifest
- Authenticates with registry
- Publishes server to registry

**Options:**
- `--tag <tag>` → Version tag
- `--access <public|private>` → Access level
- `--dry-run` → Test without publishing

**Dependencies:**
- `validate_manifest()` → Validation
- `RegistryClient` → API calls

---

#### `cpm validate`
**File:** `src/cpm/commands/validate.py`
**Function:** `validate(file, fix, ...)`
**Key Logic:**
- Validates server manifest against schema
- Can auto-fix issues

**Options:**
- `--fix` → Auto-fix issues

**Dependencies:**
- `validators.py` → Validation logic
- JSON Schema validation

---

#### `cpm login`
**File:** `src/cpm/commands/login.py`
**Function:** `login(...)`
**Key Logic:**
- Authenticates with registry (GitHub OAuth)
- Stores token locally

**Dependencies:**
- `RegistryClient` → Auth API

---

#### `cpm logout`
**File:** `src/cpm/commands/logout.py`
**Function:** `logout(...)`
**Key Logic:**
- Removes stored auth token

**Dependencies:**
- `RegistryClient`

---

#### `cpm whoami`
**File:** `src/cpm/commands/whoami.py`
**Function:** `whoami(...)`
**Key Logic:**
- Shows current authenticated user

**Dependencies:**
- `RegistryClient`

---

### F. UTILITY COMMANDS

#### `cpm doctor`
**File:** `src/cpm/commands/doctor.py`
**Function:** `doctor(verbose, fix, ...)`
**Key Logic:**
- Checks system health
- Validates configs
- Can auto-fix issues

**Checks:**
- CPM installation
- Server configurations
- Client configs
- Registry connectivity
- FastMCP availability

**Options:**
- `--verbose` → Detailed output
- `--fix` → Auto-fix issues

**Dependencies:**
- `ConfigContext`
- `ClientRegistry`
- `RegistryClient`

---

#### `cpm cache`
**File:** `src/cpm/commands/cache.py`
**Subcommands:**
- `clean` → Clear cache
- `path` → Show cache location
- `verify` → Verify cache integrity

**Functions:**
- `cache_clean()`
- `cache_path()`
- `cache_verify()`

**Dependencies:**
- `RegistryClient` → Cache management

---

#### `cpm settings`
**File:** `src/cpm/commands/settings.py`
**Subcommands:**
- `get <key>` → Get setting value
- `set <key>=<value>` → Set setting
- `reset` → Reset to defaults

**Settings:**
- `add.defaultTarget` → all|first|ask
- `install.defaultContext` → global|local
- `uninstall.purgeClients` → true|false

**Functions:**
- `settings_get(key)`
- `settings_set(key, value)`
- `settings_reset()`

**Storage:** `~/.cpm/settings.json`

**Dependencies:**
- None (simple JSON file)

---

#### `cpm upgrade`
**File:** `src/cpm/commands/upgrade.py`
**Function:** `upgrade(...)`
**Key Logic:**
- Checks for CPM updates
- Downloads and installs new version

**Dependencies:**
- PyPI API or GitHub releases

---

## 🔧 Implementation Guidelines

### Command Template
```python
# src/cpm/commands/example.py

import click
from rich.console import Console
from cpm.core.context import ConfigContext

console = Console()

@click.command()
@click.argument('arg')
@click.option('--flag', is_flag=True, help='Flag description')
@click.pass_context
def example(ctx, arg, flag):
    """Command description

    Examples:
        cpm example myarg
        cpm example myarg --flag
    """
    # Get context from CLI
    config = ConfigContext(local=ctx.obj.get('local'))

    try:
        # Command logic here
        result = config.manager.some_operation(arg)

        # Success message
        console.print(f"[green]✓[/] Operation successful")

    except Exception as e:
        # Error handling
        console.print(f"[red]Error:[/] {e}", err=True)
        raise click.Abort()
```

### Adding New Commands

1. **Create command file:** `src/cpm/commands/mycommand.py`
2. **Implement command function** with Click decorators
3. **Register in cli.py:**
   ```python
   from cpm.commands.mycommand import mycommand
   cli.add_command(mycommand)
   ```
4. **Add tests:** `tests/test_commands/test_mycommand.py`
5. **Update docs:** Add to this file and Plan.md

### @ Group Parsing Pattern

Use this helper in commands that support @groups:

```python
def parse_targets(targets, config):
    """Parse servers and @groups into server list"""
    servers = []
    for target in targets:
        if target.startswith('@'):
            # Group reference
            group_name = target[1:]
            group_servers = config.manager.get_servers_in_group(group_name)
            servers.extend(group_servers.values())
        else:
            # Server reference
            server = config.manager.get_server(target)
            servers.append(server)
    return servers
```

---

## 📚 Quick Reference

### Finding Commands
```bash
# Find command implementation
grep -r "def install" src/cpm/commands/

# Find where command is registered
grep -r "add_command(install" src/cpm/cli.py
```

### Testing Commands
```bash
# Run specific command test
pytest tests/test_commands/test_install.py

# Run all command tests
pytest tests/test_commands/

# Test with coverage
pytest --cov=cpm.commands tests/test_commands/
```

### Debugging Commands
```bash
# Run command with verbose logging
cpm --verbose install mysql

# Use pdb debugger
python -m pdb -m cpm.cli install mysql
```

---

This map provides complete coverage of all CPM commands. Use it to understand, maintain, and extend the codebase.
