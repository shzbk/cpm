"""
Data models for CPM servers and groups
"""

from datetime import datetime
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field


class BaseServerConfig(BaseModel):
    """Base configuration for all MCP servers"""

    name: str
    groups: List[str] = Field(default_factory=list)

    def add_group(self, group: str) -> None:
        """Add a group tag if not already present"""
        if group not in self.groups:
            self.groups.append(group)

    def remove_group(self, group: str) -> None:
        """Remove a group tag if present"""
        if group in self.groups:
            self.groups.remove(group)

    def has_group(self, group: str) -> bool:
        """Check if server belongs to a specific group"""
        return group in self.groups


class STDIOServerConfig(BaseServerConfig):
    """Configuration for stdio-based MCP servers"""

    command: str
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)


class RemoteServerConfig(BaseServerConfig):
    """Configuration for remote HTTP/SSE MCP servers"""

    url: str
    headers: Dict[str, str] = Field(default_factory=dict)


# Union type for all server configurations
ServerConfig = Union[STDIOServerConfig, RemoteServerConfig]


class GroupMetadata(BaseModel):
    """Metadata for a server group"""

    name: str
    description: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    model_config = {"extra": "allow"}
