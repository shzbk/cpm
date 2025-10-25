"""
Publish command - Publish MCP servers to official registry

Mirrors official mcp-publisher functionality:
  cpm publish init - Create server.json in current directory with auto-detection
  cpm publish validate - Validate server.json against official MCP schema
  cpm publish - Publish to official registry (authentication required)

Auto-detection features:
- Git repository detection (GitHub, GitLab, etc.)
- package.json analysis for npm packages
- Automatic namespace detection from git remote

Features:
- Official schema compliance (2025-10-17)
- Server.json validation
- Authentication (GitHub OAuth, OIDC)
- Namespace ownership verification
- Version management
"""

import json
import sys
from pathlib import Path
from typing import Optional

import click
import requests
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from cpm.core.schema import MCPServerConfig, Repository

console = Console()


@click.group()
def publish():
    """
    Publish MCP servers to the official registry.

    Commands:
      publish init       - Create server.json template
      publish validate   - Validate server.json against schema
      publish            - Publish server to registry

    Examples:

      \b
      cpm publish init
      cpm publish validate
      cpm publish --token $MCP_TOKEN
    """
    pass


@publish.command()
@click.option(
    "--name",
    "-n",
    help="Server name in reverse-DNS format (io.github.user/server). Auto-detected if not provided.",
)
@click.option(
    "--description",
    "-d",
    help="Server description. Auto-detected from package.json if available.",
)
@click.option(
    "--repo",
    "-r",
    help="Repository URL. Auto-detected from git remote if available.",
)
def init(
    name: Optional[str] = None,
    description: Optional[str] = None,
    repo: Optional[str] = None,
):
    """
    Create server.json template for publishing.

    Auto-detects values from:
    - Git remote URL (for namespace and server name)
    - package.json (for name and description)
    - Current directory (fallback)

    The server name must be in reverse-DNS format and match your namespace.
    """

    # Auto-detect values (matching mcp-publisher behavior)
    if not name:
        name = _detect_server_name(repo)

    if not description:
        description = _detect_description()

    if not repo:
        repo = _detect_repo_url()

    # Validate server name format
    if "/" not in name or name.count("/") != 1:
        console.print("[red]Error:[/] Server name must be in format: namespace/servername")
        console.print(f"[dim]Example:[/] io.github.myusername/myserver")
        raise click.Abort()

    namespace, servername = name.split("/")

    # Check if server.json already exists
    server_json_file = Path("server.json")
    if server_json_file.exists():
        console.print("[red]Error:[/] server.json already exists in current directory")
        console.print("[dim]Remove it first if you want to reinitialize:[/] rm server.json")
        raise click.Abort()

    console.print(f"[cyan]Creating server.json for:[/] {name}\n")

    # Create template (matches official registry schema v2025-10-17)
    template = {
        "$schema": "https://static.modelcontextprotocol.io/schemas/2025-10-17/server.schema.json",
        "name": name,
        "description": description or "TODO: Add description",
        "version": "1.0.0",
        "title": servername.replace("-", " ").title(),
        "repository": {
            "url": repo or "https://github.com/your-username/repo",
            "source": "github",
        },
        "packages": [
            {
                "registryType": "npm",
                "registryBaseUrl": "https://registry.npmjs.org",
                "identifier": f"@{namespace.replace('io.github.', '')}/{servername}",
                "version": "0.1.0",
                "runtimeHint": "npx",
                "transport": {
                    "type": "stdio",
                },
                "environmentVariables": [
                    {
                        "name": "EXAMPLE_VAR",
                        "description": "Example environment variable",
                        "isRequired": False,
                        "isSecret": False,
                        "default": "default_value",
                    }
                ],
            }
        ],
    }

    # Write server.json
    with open(server_json_file, "w") as f:
        json.dump(template, f, indent=2)

    console.print(f"[green][OK][/] Created: server.json\n")

    console.print("[yellow]TODO:[/]\n")
    console.print("  1. Update description")
    console.print("  2. Add repository information")
    console.print("  3. Configure packages/remotes")
    console.print("  4. Add environment variables")
    console.print("  5. Run: [cyan]cpm publish validate[/]")
    console.print("  6. Run: [cyan]cpm publish[/]")


@publish.command()
@click.argument("file", type=click.File("r"), default="server.json", required=False)
def validate(file):
    """
    Validate server.json against official MCP schema.

    By default validates server.json in current directory.
    """

    try:
        if isinstance(file, str):
            file_path = Path(file)
            if not file_path.exists():
                console.print(f"[red]Error:[/] File not found: {file}")
                raise click.Abort()
            data = json.loads(file_path.read_text())
        else:
            data = json.load(file)

        # Validate against MCPServerConfig schema
        server = MCPServerConfig(**data)

        console.print("[green][OK][/] Server.json is valid!\n")

        # Show server info
        table = Table(title="Server Information")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="dim")

        table.add_row("Name", server.name)
        table.add_row("Version", server.version)
        table.add_row("Description", server.description[:60] + "...")
        if server.title:
            table.add_row("Title", server.title)

        if server.packages:
            table.add_row("Packages", f"{len(server.packages)} configured")
        if server.remotes:
            table.add_row("Remotes", f"{len(server.remotes)} configured")

        console.print(table)

        console.print("\n[green]Ready to publish![/]")
        console.print("Run: [cyan]cpm publish[/]")

    except FileNotFoundError:
        console.print("[red]Error:[/] server.json not found in current directory")
        console.print("[dim]Create one with:[/] cpm publish init")
        raise click.Abort()

    except json.JSONDecodeError as e:
        console.print(f"[red]Error:[/] Invalid JSON in server.json")
        console.print(f"[dim]{e}[/]")
        raise click.Abort()

    except Exception as e:
        console.print(f"[red]Validation failed:[/]\n")
        console.print(f"[red]{str(e)}[/]")
        raise click.Abort()


@publish.command()
@click.option(
    "--token",
    "-t",
    help="Registry JWT token (from GitHub OAuth)",
    envvar="MCP_REGISTRY_TOKEN",
)
@click.option(
    "--registry",
    "-r",
    default="https://registry.modelcontextprotocol.io",
    help="Registry URL",
)
@click.option(
    "--file",
    "-f",
    default="server.json",
    help="Path to server.json file",
)
def publish_server(
    token: Optional[str] = None,
    registry: str = "https://registry.modelcontextprotocol.io",
    file: str = "server.json",
):
    """
    Publish server to the official MCP registry.

    Requires authentication token (from GitHub OAuth).
    See: https://registry.modelcontextprotocol.io/docs for authentication.
    """

    # Load and validate server.json
    server_path = Path(file)
    if not server_path.exists():
        console.print(f"[red]Error:[/] File not found: {file}")
        console.print("[dim]Create one with:[/] cpm publish init --name your/server")
        raise click.Abort()

    try:
        with open(server_path) as f:
            server_data = json.load(f)
        server = MCPServerConfig(**server_data)
    except json.JSONDecodeError as e:
        console.print(f"[red]Error:[/] Invalid JSON: {e}")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Validation failed:[/] {e}")
        raise click.Abort()

    # Get token if not provided
    if not token:
        console.print(
            "\n[yellow]Authentication Required[/]\n"
        )
        console.print(
            "Get your token from: [cyan]https://registry.modelcontextprotocol.io/auth/github[/]\n"
        )
        token = Prompt.ask("Paste your registry JWT token")

        if not token:
            console.print("[red]Error:[/] Token required to publish")
            raise click.Abort()

    # Publish to registry
    console.print(f"\n[cyan]Publishing {server.name}...[/]\n")

    try:
        publish_url = f"{registry}/v0.1/publish"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = requests.post(
            publish_url,
            json=server_data,
            headers=headers,
            timeout=30,
        )

        if response.status_code == 200:
            console.print("[green][OK][/] Server published successfully!\n")

            result = response.json()
            if "_meta" in result:
                meta = result["_meta"]["io.modelcontextprotocol.registry/official"]
                console.print(f"Status: [green]{meta['status']}[/]")
                console.print(f"Published: {meta['publishedAt']}")

            console.print(
                f"\n[dim]View on registry:[/] [cyan]"
                f"{registry}/servers?name={server.name}[/cyan]"
            )

        elif response.status_code == 401:
            console.print("[red]Error:[/] Invalid or expired authentication token")
            console.print("[dim]Get a new token at:[/] https://registry.modelcontextprotocol.io/auth")
            raise click.Abort()

        elif response.status_code == 403:
            console.print("[red]Error:[/] Permission denied")
            console.print("[dim]You don't have permission to publish this server.")
            console.print("[dim]Namespace ownership must be verified.")
            raise click.Abort()

        else:
            error_msg = response.text
            try:
                error_data = response.json()
                error_msg = error_data.get("error", error_msg)
            except:
                pass

            console.print(f"[red]Error ({response.status_code}):[/] {error_msg}")
            raise click.Abort()

    except requests.RequestException as e:
        console.print(f"[red]Error:[/] Failed to connect to registry")
        console.print(f"[dim]{e}[/]")
        raise click.Abort()


# ============================================================================
# Auto-Detection Helper Functions (matches mcp-publisher behavior)
# ============================================================================


def _detect_repo_url() -> str:
    """
    Detect repository URL from git remote.

    Matches mcp-publisher's detectRepoURL() function.
    """
    import subprocess

    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass

    return "https://github.com/your-username/your-repo.git"


def _detect_server_name(repo_url: Optional[str] = None) -> str:
    """
    Auto-detect server name from git repository or package.json.

    Matches mcp-publisher's detectServerName() function:
    - GitHub: github.com/owner/repo → io.github.owner/repo
    - package.json @org/pkg → io.github.org/pkg
    - Fallback: com.example/dirname
    """

    # Try from git remote
    if not repo_url:
        repo_url = _detect_repo_url()

    if repo_url and "github.com" in repo_url:
        # Extract owner/repo from GitHub URL
        # Format: https://github.com/owner/repo.git or https://github.com/owner/repo
        parts = repo_url.rstrip("/").split("/")
        if len(parts) >= 2:
            owner = parts[-2]
            repo = parts[-1].removesuffix(".git")
            return f"io.github.{owner}/{repo}"

    # Try from package.json
    try:
        with open("package.json") as f:
            pkg = json.load(f)
            pkg_name = pkg.get("name", "")
            if pkg_name:
                # @org/package → io.github.org/package
                if pkg_name.startswith("@"):
                    parts = pkg_name[1:].split("/")
                    if len(parts) == 2:
                        return f"io.github.{parts[0]}/{parts[1]}"
                # package → io.github.user/package (needs user input)
                return f"io.github.<your-username>/{pkg_name}"
    except Exception:
        pass

    # Fallback to current directory
    try:
        import os
        dirname = os.path.basename(os.getcwd())
        return f"com.example/{dirname}"
    except Exception:
        pass

    return "com.example/my-mcp-server"


def _detect_description() -> str:
    """
    Auto-detect description from package.json.

    Matches mcp-publisher's detectDescription() function.
    """
    try:
        with open("package.json") as f:
            pkg = json.load(f)
            desc = pkg.get("description", "")
            if desc:
                return desc
    except Exception:
        pass

    return "MCP server providing useful functionality"


def _detect_package_type() -> str:
    """Detect package type from environment."""
    try:
        with open("package.json") as f:
            json.load(f)
            return "npm"
    except Exception:
        pass

    # Try for Python
    if Path("setup.py").exists() or Path("pyproject.toml").exists():
        return "pypi"

    # Try for Docker
    if Path("Dockerfile").exists():
        return "oci"

    return "npm"  # Default to npm
