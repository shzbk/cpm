"""
Pytest configuration and fixtures
"""

import pytest


@pytest.fixture
def temp_config_dir(tmp_path):
    """Provide a temporary config directory for tests"""
    config_dir = tmp_path / ".config" / "cpm"
    config_dir.mkdir(parents=True)
    return config_dir
