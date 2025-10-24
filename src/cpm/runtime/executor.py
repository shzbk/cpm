"""
Server executor using FastMCP
"""

import logging
from typing import Optional

from fastmcp import FastMCP
from rich.console import Console
from rich.panel import Panel

from cpm.core.schema import RemoteServerConfig, ServerConfig, STDIOServerConfig

logger = logging.getLogger(__name__)
console = Console()


class ServerExecutor:
    """
    Executes MCP servers using FastMCP

    Supports:
    - stdio mode (default)
    - HTTP mode
    - SSE mode
    """

    async def run_stdio(self, server: ServerConfig) -> None:
        """Run server in stdio mode"""
        proxy = await self._create_proxy(server)
        await proxy.run_stdio_async(show_banner=False)

    async def run_http(
        self,
        server: ServerConfig,
        port: int = 6276,
        host: str = "127.0.0.1",
        sse: bool = False,
    ) -> None:
        """Run server in HTTP or SSE mode"""
        proxy = await self._create_proxy(server)

        # Display server info
        mode = "SSE" if sse else "HTTP"
        url = f"http://{host}:{port}/"
        transport = "sse" if sse else "http"

        panel_content = (
            f"[bold]Server:[/] {server.name}\n"
            f"[bold]Mode:[/] {mode}\n"
            f"[bold]URL:[/] [cyan]{url}[/cyan]\n\n"
            f"[dim]Press Ctrl+C to stop[/]"
        )
        panel = Panel(
            panel_content,
            title=f"[*] {mode} Server Running",
            border_style="green",
            padding=(1, 2),
        )
        console.print(panel)

        # Run server
        await proxy.run_http_async(
            host=host,
            port=port,
            transport=transport,
            show_banner=False,
        )

    async def _create_proxy(self, server: ServerConfig) -> FastMCP:
        """Create FastMCP proxy for a server"""
        try:
            # Try new import path (fastmcp >= 2.12)
            from fastmcp.mcp_config import (
                MCPConfig,
                RemoteMCPServer,
                StdioMCPServer,
            )
        except ImportError:
            # Fallback to old import path (fastmcp < 2.12)
            from fastmcp.utilities.mcp_config import (
                MCPConfig,
                RemoteMCPServer,
                StdioMCPServer,
            )

        # Build MCP config
        if isinstance(server, STDIOServerConfig):
            mcp_server = StdioMCPServer(
                command=server.command,
                args=server.args or [],
                env=server.env or {},
            )
        elif isinstance(server, RemoteServerConfig):
            mcp_server = RemoteMCPServer(
                url=server.url,
                headers=server.headers or {},
            )
        else:
            raise ValueError(f"Unsupported server type: {type(server)}")

        # Create proxy
        config = MCPConfig(mcpServers={server.name: mcp_server})
        proxy = FastMCP.as_proxy(config, name=f"cpm-{server.name}")

        return proxy
