"""
Serve MCP server(s) as HTTP (alias for run --http)
"""

import click
from rich.console import Console

console = Console()


@click.command()
@click.argument("target")
@click.option("-p", "--port", default=6276, type=int, help="Port to serve on (default: 6276)")
@click.option("--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
@click.pass_context
def serve(ctx, target, port, host):
    """
    Serve server(s) as HTTP server (alias for run --http)

    TARGET can be a server name or @group name.

    Examples:

        \b
        cpm serve mysql                       # Serve mysql on default port (6276)
        cpm serve mysql -p 9000               # Serve on port 9000
        cpm serve @database                   # Serve entire group
        cpm serve mysql --host 0.0.0.0        # Expose on network
    """
    # Import run command
    from cpm.commands.run import run

    # Call run command with http=True
    ctx.invoke(run, target=target, http=True, port=port, host=host)
