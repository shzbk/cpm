"""
ServerConfigAdapter - Converts MCP registry format to CPM runtime format

Handles:
- Selecting best package/transport option
- Generating execution commands from package type
- Extracting environment variables
- Creating runtime configurations
"""

import logging
from typing import Dict, List, Optional, Tuple

from cpm.core.schema import (
    CPMRuntimeConfig,
    MCPServerConfig,
    Package,
    StreamableHttpTransport,
    SseTransport,
    StdioTransport,
)

logger = logging.getLogger(__name__)


class ServerConfigAdapter:
    """
    Adapts MCP ServerJSON (from registry) to CPM runtime configuration.

    MCP format is standardized and rich with metadata.
    CPM runtime format is optimized for execution and installation.
    """

    @staticmethod
    def adapt(
        server_json: MCPServerConfig,
        simple_name: Optional[str] = None,
        env_overrides: Optional[Dict[str, str]] = None,
    ) -> CPMRuntimeConfig:
        """
        Convert MCP ServerJSON to CPM runtime configuration.

        Args:
            server_json: Full MCP server configuration from registry
            simple_name: Optional simple name (defaults to last part of full name)
            env_overrides: Optional environment variable overrides

        Returns:
            CPMRuntimeConfig ready for execution

        Raises:
            ValueError: If server has no valid installation method
        """

        # Determine simple name if not provided
        if not simple_name:
            # Extract simple name from reverse-DNS (io.github.user/mysql -> mysql)
            simple_name = server_json.name.split("/")[-1]

        # Determine installation method and get configuration
        if server_json.packages:
            return ServerConfigAdapter._adapt_package(
                server_json,
                simple_name,
                env_overrides,
            )
        elif server_json.remotes:
            return ServerConfigAdapter._adapt_remote(
                server_json,
                simple_name,
                env_overrides,
            )
        else:
            raise ValueError(
                f"Server {server_json.name} has no packages or remotes configured"
            )

    @staticmethod
    def _adapt_package(
        server_json: MCPServerConfig,
        simple_name: str,
        env_overrides: Optional[Dict[str, str]] = None,
    ) -> CPMRuntimeConfig:
        """
        Adapt package-based server (npm, pypi, oci, nuget, mcpb).

        Selects best package option and generates execution command.
        """

        package = ServerConfigAdapter._select_best_package(server_json.packages)
        logger.debug(
            f"Selected package for {server_json.name}: "
            f"{package.registryType}/{package.identifier}"
        )

        # Generate command based on registry type and transport
        command, args = ServerConfigAdapter._generate_command(
            package,
            server_json.name,
        )

        # Extract environment variables
        env_vars = ServerConfigAdapter._extract_env_vars(
            package,
            env_overrides,
        )

        return CPMRuntimeConfig(
            name=simple_name,
            registry_name=server_json.name,
            install_method="stdio",
            command=command,
            args=args,
            env=env_vars,
            original_config=server_json,
        )

    @staticmethod
    def _adapt_remote(
        server_json: MCPServerConfig,
        simple_name: str,
        env_overrides: Optional[Dict[str, str]] = None,
    ) -> CPMRuntimeConfig:
        """
        Adapt remote server (streamable-http or sse).

        Selects best transport option.
        """

        # Prefer streamable-http over sse
        remote = ServerConfigAdapter._select_best_remote(server_json.remotes)
        logger.debug(
            f"Selected remote for {server_json.name}: {remote.type} - {remote.url}"
        )

        # Extract headers as environment variables if needed
        headers = {}
        if hasattr(remote, "headers") and remote.headers:
            for header in remote.headers:
                headers[header.name] = header.value or ""

        # Apply overrides
        if env_overrides:
            headers.update(env_overrides)

        return CPMRuntimeConfig(
            name=simple_name,
            registry_name=server_json.name,
            install_method=remote.type,  # "streamable-http" or "sse"
            url=remote.url,
            headers=headers,
            env=headers,  # For consistency with env vars
            original_config=server_json,
        )

    @staticmethod
    def _select_best_package(packages: List[Package]) -> Package:
        """
        Select best package from list.

        Priority:
        1. Package with stdio transport (most compatible)
        2. First package in list
        """

        if not packages:
            raise ValueError("No packages available")

        # Try to find stdio package
        for pkg in packages:
            if isinstance(pkg.transport, StdioTransport):
                return pkg

        # Fall back to first package
        logger.warning(
            f"No stdio transport found, using first package: "
            f"{packages[0].registryType}/{packages[0].identifier}"
        )
        return packages[0]

    @staticmethod
    def _select_best_remote(
        remotes: List
    ) -> Tuple[StreamableHttpTransport | SseTransport]:
        """
        Select best remote from list.

        Priority:
        1. streamable-http (more compatible)
        2. sse
        """

        if not remotes:
            raise ValueError("No remotes available")

        # Prefer streamable-http
        for remote in remotes:
            if isinstance(remote, StreamableHttpTransport):
                return remote

        # Fall back to sse
        if remotes:
            return remotes[0]

        raise ValueError("No suitable remote transport found")

    @staticmethod
    def _generate_command(
        package: Package,
        server_name: str,
    ) -> Tuple[str, List[str]]:
        """
        Generate execution command for package.

        Maps registry type to runtime command and arguments.
        """

        registry_type = package.registryType.lower()
        identifier = package.identifier
        version = package.version
        runtime_hint = package.runtimeHint

        # Generate command based on registry type
        if registry_type == "npm":
            # npm packages via npx
            command = runtime_hint or "npx"
            args = ["-y", identifier]  # -y to skip confirmation

        elif registry_type == "pypi":
            # Python packages via uvx (uv tool)
            command = runtime_hint or "uvx"
            args = [identifier]

        elif registry_type == "oci":
            # OCI container images via docker
            command = runtime_hint or "docker"
            args = ["run", "--rm", identifier]

        elif registry_type == "nuget":
            # .NET packages
            command = runtime_hint or "dotnet"
            args = ["tool", "run", identifier]

        elif registry_type == "mcpb":
            # Direct binary download
            command = "curl"
            args = ["-L", "-o", f"{identifier.split('/')[-1]}", identifier]

        else:
            # Unknown type - use hint if provided
            if not runtime_hint:
                raise ValueError(
                    f"Unknown registry type '{registry_type}' and no runtimeHint provided"
                )
            command = runtime_hint
            args = [identifier]

        # Add package arguments if specified
        if package.packageArguments:
            for arg in package.packageArguments:
                if arg.type == "positional":
                    args.append(arg.value or "")
                elif arg.type == "named":
                    args.append(arg.name or "")
                    if arg.value:
                        args.append(arg.value)

        logger.debug(f"Generated command for {server_name}: {command} {' '.join(args)}")

        return command, args

    @staticmethod
    def _extract_env_vars(
        package: Package,
        env_overrides: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """
        Extract environment variables from package.

        Returns dict of env vars with defaults applied.
        """

        env_vars = {}

        if package.environmentVariables:
            for env_var in package.environmentVariables:
                # Use override if provided, else use default
                if env_overrides and env_var.name in env_overrides:
                    env_vars[env_var.name] = env_overrides[env_var.name]
                elif env_var.default:
                    env_vars[env_var.name] = env_var.default
                else:
                    # Leave empty for required vars without defaults
                    env_vars[env_var.name] = ""

                logger.debug(
                    f"Extracted env var: {env_var.name} "
                    f"(required={env_var.isRequired}, secret={env_var.isSecret})"
                )

        # Apply any additional overrides
        if env_overrides:
            env_vars.update(env_overrides)

        return env_vars

    @staticmethod
    def get_missing_required_vars(config: CPMRuntimeConfig) -> List[str]:
        """
        Get list of required environment variables not yet configured.

        Used for configuration validation before running.
        """

        if not config.original_config or not config.original_config.packages:
            return []

        missing = []
        package = config.original_config.packages[0]

        if package.environmentVariables:
            for env_var in package.environmentVariables:
                if env_var.isRequired:
                    # Check if configured
                    if not config.env.get(env_var.name):
                        missing.append(env_var.name)

        return missing
