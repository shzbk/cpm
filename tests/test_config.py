"""
Tests for GlobalConfigManager
"""

import pytest

from cpm.core import GlobalConfigManager, STDIOServerConfig


def test_add_server(temp_config_dir):
    """Test adding a server"""
    config = GlobalConfigManager(config_path=temp_config_dir / "servers.json")

    server = STDIOServerConfig(
        name="test-server",
        command="npx",
        args=["-y", "test"],
    )

    assert config.add_server(server) is True
    assert config.server_exists("test-server") is True


def test_remove_server(temp_config_dir):
    """Test removing a server"""
    config = GlobalConfigManager(config_path=temp_config_dir / "servers.json")

    server = STDIOServerConfig(name="test-server", command="npx")
    config.add_server(server)

    assert config.remove_server("test-server") is True
    assert config.server_exists("test-server") is False


def test_profile_tagging(temp_config_dir):
    """Test profile tagging system"""
    config = GlobalConfigManager(config_path=temp_config_dir / "servers.json")

    # Create server
    server = STDIOServerConfig(name="test-server", command="npx")
    config.add_server(server)

    # Add to profile
    assert config.add_server_to_profile("test-server", "test-profile") is True

    # Check profile
    servers = config.get_servers_in_profile("test-profile")
    assert "test-server" in servers
    assert servers["test-server"].has_profile_tag("test-profile")
