"""
Validate command - Check configuration status of all servers
"""

import click
from rich.console import Console
from rich.table import Table

from cpm.core.context import ConfigContext
from cpm.utils.config_validator import ConfigValidator

console = Console()


@click.command()
@click.option("--local", is_flag=True, help="Validate local project servers")
@click.option("--json", "json_output", is_flag=True, help="JSON output format")
@click.pass_context
def validate(ctx, local: bool, json_output: bool):
    """
    Validate configuration status of all installed servers

    Shows which servers are properly configured and which need attention.

    Examples:

        cpm validate                 # Check all servers
        cpm validate --local         # Check local project servers
        cpm validate --json          # JSON output
    """
    config = ConfigContext(local=local or ctx.obj.get("local", False))

    servers = config.list_servers()

    if not servers:
        console.print("[yellow]No servers installed[/]")
        return

    if json_output:
        _validate_json(servers)
    else:
        _validate_pretty(servers)


def _validate_pretty(servers):
    """Display validation results in human-readable format"""
    table = Table(title="Server Configuration Status")
    table.add_column("Server", style="cyan")
    table.add_column("Status", style="dim")
    table.add_column("Details", style="dim")

    ready_count = 0
    incomplete_count = 0
    issues = []

    for name, server in servers.items():
        missing = ConfigValidator.get_missing_vars(server)
        configured, total = ConfigValidator.get_configured_count(server)

        if not missing:
            status = "[green]READY[/]"
            details = "(all configured)"
            ready_count += 1
        else:
            status = "[yellow]INCOMPLETE[/]"
            details = "({}/{} configured)".format(configured, total)
            incomplete_count += 1
            issues.append((name, missing))

        table.add_row(name, status, details)

    console.print(table)
    console.print()

    # Summary
    console.print(f"[dim]Summary:[/]")
    console.print(f"  Ready: {ready_count}")
    console.print(f"  Incomplete: {incomplete_count}")

    # Issues
    if issues:
        console.print()
        console.print("[yellow]Issues found:[/]")
        for server_name, missing_vars in issues:
            console.print(f"\n  {server_name}: Missing {len(missing_vars)} variable(s)")
            for var in missing_vars:
                console.print(f"    - {var}")

        console.print()
        console.print("[dim]Fix with:[/]")
        for server_name, _ in issues:
            console.print(f"  cpm config {server_name}")
    else:
        console.print()
        console.print("[green]All servers are properly configured![/]")


def _validate_json(servers):
    """Output validation results as JSON"""
    import json

    output = {
        "summary": {
            "total": len(servers),
            "ready": 0,
            "incomplete": 0
        },
        "servers": {}
    }

    for name, server in servers.items():
        missing = ConfigValidator.get_missing_vars(server)
        configured, total = ConfigValidator.get_configured_count(server)

        is_configured = len(missing) == 0

        if is_configured:
            output["summary"]["ready"] += 1
        else:
            output["summary"]["incomplete"] += 1

        output["servers"][name] = {
            "configured": is_configured,
            "missing": missing,
            "configured_vars": configured,
            "total_vars": total
        }

    print(json.dumps(output, indent=2))
