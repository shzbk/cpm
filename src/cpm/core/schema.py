"""
Data models for CPM - Aligned with MCP Official Registry ServerJSON Standard

Reference: https://static.modelcontextprotocol.io/schemas/2025-10-17/server.schema.json
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# TRANSPORT TYPES (from MCP Standard)
# ============================================================================

class StdioTransport(BaseModel):
    """Standard input/output transport"""

    type: Literal["stdio"] = "stdio"


class StreamableHttpTransport(BaseModel):
    """Streamable HTTP transport for long-running connections"""

    type: Literal["streamable-http"] = "streamable-http"
    url: str = Field(..., description="HTTP endpoint URL")


class SseTransport(BaseModel):
    """Server-sent events transport"""

    type: Literal["sse"] = "sse"
    url: str = Field(..., description="SSE endpoint URL")


Transport = Union[StdioTransport, StreamableHttpTransport, SseTransport]


# ============================================================================
# INPUT TYPES (from MCP Standard)
# ============================================================================

class Input(BaseModel):
    """Base input configuration"""

    description: Optional[str] = None
    isRequired: bool = Field(default=False)
    format: Optional[str] = Field(
        default="string",
        description="string|number|boolean|filepath"
    )
    value: Optional[str] = None
    isSecret: bool = Field(default=False)
    default: Optional[str] = None
    placeholder: Optional[str] = None
    choices: Optional[List[str]] = None

    model_config = {"extra": "allow"}


class InputWithVariables(Input):
    """Input with variable substitution"""

    variables: Optional[Dict[str, Input]] = None


class KeyValueInput(InputWithVariables):
    """Key-value pair (header or environment variable)"""

    name: str = Field(..., description="Variable or header name")


class Argument(InputWithVariables):
    """Command-line argument"""

    type: str = Field(..., description="positional|named")
    name: Optional[str] = None  # For named arguments
    valueHint: Optional[str] = None  # For positional arguments
    isRepeated: bool = Field(default=False)


# ============================================================================
# ICON TYPE (from MCP Standard)
# ============================================================================

class Icon(BaseModel):
    """Server icon configuration"""

    src: str = Field(..., description="HTTPS URL to icon")
    mimeType: Optional[str] = None
    sizes: Optional[List[str]] = None
    theme: Optional[str] = None  # light|dark


# ============================================================================
# REPOSITORY TYPE (from MCP Standard)
# ============================================================================

class Repository(BaseModel):
    """Source code repository information"""

    url: str = Field(..., description="Repository URL")
    source: str = Field(..., description="Repository host: github, gitlab, etc.")
    id: Optional[str] = None  # Repository ID from hosting service
    subfolder: Optional[str] = None  # For monorepos


# ============================================================================
# PACKAGE TYPE (from MCP Standard)
# ============================================================================

class Package(BaseModel):
    """Package configuration for installation"""

    registryType: str = Field(
        ...,
        description="npm|pypi|oci|nuget|mcpb"
    )
    identifier: str = Field(..., description="Package name or image reference")
    version: Optional[str] = Field(
        default=None,
        description="Specific package version (not ranges)"
    )
    registryBaseUrl: Optional[str] = None  # URL to package registry
    fileSha256: Optional[str] = None  # SHA256 hash for integrity
    runtimeHint: Optional[str] = None  # npx|uvx|docker|etc
    transport: Transport = Field(..., description="Transport configuration")
    runtimeArguments: Optional[List[Argument]] = None
    packageArguments: Optional[List[Argument]] = None
    environmentVariables: Optional[List[KeyValueInput]] = None


# ============================================================================
# SERVER CONFIGURATION (from MCP Standard - renamed to MCPServerConfig)
# ============================================================================

class MCPServerConfig(BaseModel):
    """
    Complete MCP Server configuration aligned with official registry format.

    This is the primary server definition format for CPM.
    Replaces the old STDIOServerConfig and RemoteServerConfig.
    Follows: https://static.modelcontextprotocol.io/schemas/2025-10-17/server.schema.json
    """

    schema: str = Field(
        default="https://static.modelcontextprotocol.io/schemas/2025-10-17/server.schema.json",
        alias="$schema"
    )
    name: str = Field(
        ...,
        description="Server name in reverse-DNS format (io.github.user/server)"
    )
    description: str = Field(
        ...,
        description="Human-readable server description"
    )
    version: str = Field(..., description="Semantic version string")
    status: Optional[str] = Field(default="active", description="Server status (active, deprecated, deleted, etc)")
    title: Optional[str] = None  # Display name
    websiteUrl: Optional[str] = None  # Homepage/docs URL
    repository: Optional[Repository] = None
    icons: Optional[List[Icon]] = None
    packages: Optional[List[Package]] = None  # For installable packages
    remotes: Optional[List[Union[StreamableHttpTransport, SseTransport]]] = None  # For remote servers

    model_config = {"populate_by_name": True}  # Allow both $schema and schema

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """Enforce reverse-DNS naming convention"""
        if "/" not in v:
            raise ValueError("Name must be in reverse-DNS format: namespace/servername")
        parts = v.split("/")
        if len(parts) != 2:
            raise ValueError("Name must contain exactly one forward slash")
        return v

    def has_stdio_option(self) -> bool:
        """Check if server can run via stdio"""
        if self.packages:
            for pkg in self.packages:
                if isinstance(pkg.transport, StdioTransport):
                    return True
        return False

    def has_remote_option(self) -> bool:
        """Check if server has remote endpoint"""
        return bool(self.remotes)

    def get_best_package(self) -> Optional[Package]:
        """Get recommended package (first if multiple exist)"""
        return self.packages[0] if self.packages else None

    def get_best_remote(self) -> Optional[Union[StreamableHttpTransport, SseTransport]]:
        """Get recommended remote (streamable-http preferred over sse)"""
        if not self.remotes:
            return None
        for remote in self.remotes:
            if isinstance(remote, StreamableHttpTransport):
                return remote
        return self.remotes[0] if self.remotes else None


# ============================================================================
# CPM-SPECIFIC RUNTIME CONFIG (Internal Use)
# ============================================================================

class CPMRuntimeConfig(BaseModel):
    """
    CPM internal runtime configuration.

    Derived from MCPServerConfig for execution/installation.
    Not published to registry - used locally only.
    """

    # Server identity
    name: str  # Simple name or full reverse-DNS name
    registry_name: str  # Full reverse-DNS name (io.github.user/server)
    registry_url: Optional[str] = None  # URL to registry entry

    # Installation details
    install_method: str = Field(description="stdio|remote|package")

    # For stdio execution
    command: Optional[str] = None  # uvx, npx, docker, etc
    args: Optional[List[str]] = Field(default_factory=list)

    # For remote servers
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = Field(default_factory=dict)

    # Environment and configuration
    env: Dict[str, str] = Field(default_factory=dict)

    # Groups for organization (CPM feature)
    groups: List[str] = Field(default_factory=list)

    # Original server config for reference
    original_config: Optional[MCPServerConfig] = None

    def add_group(self, group: str) -> None:
        """Add server to a group"""
        if group not in self.groups:
            self.groups.append(group)

    def remove_group(self, group: str) -> None:
        """Remove server from a group"""
        if group in self.groups:
            self.groups.remove(group)

    def has_group(self, group: str) -> bool:
        """Check if server belongs to a group"""
        return group in self.groups


# ============================================================================
# PROJECT MANIFEST (server.json)
# ============================================================================

class ServerManifest(BaseModel):
    """
    Project-level server manifest (server.json).

    Equivalent to package.json in npm.
    """

    name: str  # Project name
    version: str = Field(default="1.0.0")
    description: Optional[str] = None

    # Server dependencies
    servers: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of simple_name -> version_specifier"
    )
    devServers: Dict[str, str] = Field(
        default_factory=dict,
        description="Dev-only servers"
    )

    # Group organization
    groups: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Group name -> list of server names"
    )

    # Environment configuration
    config: Dict[str, Dict[str, str]] = Field(
        default_factory=dict,
        description="Per-server env var overrides"
    )


# ============================================================================
# LOCKFILE (server-lock.json)
# ============================================================================

class ServerLockEntry(BaseModel):
    """Single server entry in lockfile"""

    resolved: str  # Full registry name (io.github.user/server)
    version: str  # Pinned version
    registryMetadata: MCPServerConfig  # Full server config from registry
    integrity: Optional[str] = None  # Hash for integrity checking
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ServerLockfile(BaseModel):
    """
    Lock file (server-lock.json).

    Equivalent to package-lock.json in npm.
    Pins exact versions and stores registry metadata.
    """

    lockfileVersion: int = Field(default=1)
    servers: Dict[str, ServerLockEntry] = Field(
        default_factory=dict,
        description="Installed servers with pinned versions"
    )


# ============================================================================
# GROUP METADATA
# ============================================================================

class GroupMetadata(BaseModel):
    """CPM group metadata"""

    name: str
    description: Optional[str] = None
    servers: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# BACKWARD COMPATIBILITY ALIASES
# ============================================================================

# Main config types used throughout codebase
ServerConfig = Union[MCPServerConfig, CPMRuntimeConfig]

# Executor expects these types - both are CPMRuntimeConfig
STDIOServerConfig = CPMRuntimeConfig
RemoteServerConfig = CPMRuntimeConfig
