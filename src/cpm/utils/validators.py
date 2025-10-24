"""
Validation utilities for server manifests and configurations
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pydantic import ValidationError

from cpm.core.schema import STDIOServerConfig, RemoteServerConfig


def validate_server_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate server name format

    Args:
        name: Server name to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name:
        return False, "Server name cannot be empty"

    # Check length
    if len(name) < 2:
        return False, "Server name must be at least 2 characters"

    if len(name) > 214:
        return False, "Server name must be less than 214 characters"

    # Check format (alphanumeric, dash, underscore)
    if not re.match(r"^[a-z0-9_-]+$", name):
        return False, "Server name can only contain lowercase letters, numbers, dashes, and underscores"

    # Check reserved names
    reserved = ["node_modules", "favicon.ico"]
    if name in reserved:
        return False, f"Server name '{name}' is reserved"

    return True, None


def validate_version(version: str) -> Tuple[bool, Optional[str]]:
    """
    Validate version format (semver)

    Args:
        version: Version string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not version:
        return False, "Version cannot be empty"

    # Allow "latest" and "linked"
    if version in ["latest", "linked"]:
        return True, None

    # Semver pattern
    semver_pattern = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"

    if not re.match(semver_pattern, version):
        return False, "Version must be valid semver (e.g., 1.0.0, 1.2.3-alpha.1)"

    return True, None


def validate_server_config(config: Dict) -> Tuple[bool, List[str]]:
    """
    Validate server configuration

    Args:
        config: Server configuration dictionary

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Check required fields
    if "name" not in config:
        errors.append("Missing required field: name")
    else:
        # Validate name
        is_valid, error = validate_server_name(config["name"])
        if not is_valid:
            errors.append(f"Invalid name: {error}")

    # Check server type
    has_command = "command" in config
    has_url = "url" in config

    if not has_command and not has_url:
        errors.append("Server must have either 'command' (stdio) or 'url' (remote)")

    if has_command and has_url:
        errors.append("Server cannot have both 'command' and 'url'")

    # Validate based on type
    if has_command:
        # STDIO server
        if not config["command"]:
            errors.append("Command cannot be empty")

        if "args" in config and not isinstance(config["args"], list):
            errors.append("Args must be a list")

        if "env" in config and not isinstance(config["env"], dict):
            errors.append("Env must be a dictionary")

    if has_url:
        # Remote server
        if not config["url"]:
            errors.append("URL cannot be empty")

        # Basic URL validation
        url = config["url"]
        if not (url.startswith("http://") or url.startswith("https://")):
            errors.append("URL must start with http:// or https://")

        if "headers" in config and not isinstance(config["headers"], dict):
            errors.append("Headers must be a dictionary")

    # Validate version if present
    if "version" in config:
        is_valid, error = validate_version(config["version"])
        if not is_valid:
            errors.append(f"Invalid version: {error}")

    return len(errors) == 0, errors


def validate_manifest(manifest_path: Path) -> Tuple[bool, List[str]]:
    """
    Validate server manifest file (server.json or package.json)

    Args:
        manifest_path: Path to manifest file

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Check file exists
    if not manifest_path.exists():
        return False, [f"Manifest file not found: {manifest_path}"]

    # Parse JSON
    try:
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]
    except Exception as e:
        return False, [f"Failed to read manifest: {e}"]

    # Validate as server config
    is_valid, config_errors = validate_server_config(manifest)
    errors.extend(config_errors)

    # Additional manifest checks
    if "description" in manifest:
        if not isinstance(manifest["description"], str):
            errors.append("Description must be a string")

    if "author" in manifest:
        if not isinstance(manifest["author"], (str, dict)):
            errors.append("Author must be a string or object")

    if "license" in manifest:
        if not isinstance(manifest["license"], str):
            errors.append("License must be a string")

    return len(errors) == 0, errors


def validate_local_manifest(manifest_path: Path) -> Tuple[bool, List[str]]:
    """
    Validate local project manifest (cpm.json)

    Args:
        manifest_path: Path to cpm.json

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Check file exists
    if not manifest_path.exists():
        return False, [f"Manifest file not found: {manifest_path}"]

    # Parse JSON
    try:
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]
    except Exception as e:
        return False, [f"Failed to read manifest: {e}"]

    # Check required fields
    if "name" not in manifest:
        errors.append("Missing required field: name")
    else:
        is_valid, error = validate_server_name(manifest["name"])
        if not is_valid:
            errors.append(f"Invalid project name: {error}")

    if "version" in manifest:
        is_valid, error = validate_version(manifest["version"])
        if not is_valid:
            errors.append(f"Invalid project version: {error}")

    # Validate servers section
    if "servers" in manifest:
        if not isinstance(manifest["servers"], dict):
            errors.append("Servers must be a dictionary")
        else:
            for name, version in manifest["servers"].items():
                is_valid, error = validate_server_name(name)
                if not is_valid:
                    errors.append(f"Invalid server name '{name}': {error}")

                is_valid, error = validate_version(version)
                if not is_valid:
                    errors.append(f"Invalid version for '{name}': {error}")

    # Validate devServers section
    if "devServers" in manifest:
        if not isinstance(manifest["devServers"], dict):
            errors.append("DevServers must be a dictionary")
        else:
            for name, version in manifest["devServers"].items():
                is_valid, error = validate_server_name(name)
                if not is_valid:
                    errors.append(f"Invalid dev server name '{name}': {error}")

                is_valid, error = validate_version(version)
                if not is_valid:
                    errors.append(f"Invalid version for dev server '{name}': {error}")

    # Validate groups section
    if "groups" in manifest:
        if not isinstance(manifest["groups"], dict):
            errors.append("Groups must be a dictionary")
        else:
            for group_name, servers in manifest["groups"].items():
                if not isinstance(servers, list):
                    errors.append(f"Group '{group_name}' must be a list of servers")

    # Validate config section
    if "config" in manifest:
        if not isinstance(manifest["config"], dict):
            errors.append("Config must be a dictionary")
        else:
            for server_name, env_vars in manifest["config"].items():
                if not isinstance(env_vars, dict):
                    errors.append(f"Config for '{server_name}' must be a dictionary")

    return len(errors) == 0, errors


def validate_env_vars(env_vars: Dict[str, str]) -> Tuple[bool, List[str]]:
    """
    Validate environment variables

    Args:
        env_vars: Dictionary of environment variables

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    for key, value in env_vars.items():
        # Check key format
        if not re.match(r"^[A-Z_][A-Z0-9_]*$", key):
            errors.append(f"Invalid env var name '{key}': must be uppercase with underscores")

        # Check value is string
        if not isinstance(value, str):
            errors.append(f"Env var '{key}' value must be a string")

    return len(errors) == 0, errors


def auto_fix_manifest(manifest: Dict) -> Tuple[Dict, List[str]]:
    """
    Attempt to auto-fix common manifest issues

    Args:
        manifest: Manifest dictionary

    Returns:
        Tuple of (fixed_manifest, list_of_fixes)
    """
    fixed = manifest.copy()
    fixes = []

    # Fix name (lowercase)
    if "name" in fixed and fixed["name"] != fixed["name"].lower():
        fixed["name"] = fixed["name"].lower()
        fixes.append("Converted name to lowercase")

    # Fix args to list
    if "args" in fixed and not isinstance(fixed["args"], list):
        if isinstance(fixed["args"], str):
            fixed["args"] = [fixed["args"]]
            fixes.append("Converted args string to list")

    # Fix env to dict
    if "env" in fixed and not isinstance(fixed["env"], dict):
        fixed["env"] = {}
        fixes.append("Reset env to empty dictionary")

    # Fix headers to dict
    if "headers" in fixed and not isinstance(fixed["headers"], dict):
        fixed["headers"] = {}
        fixes.append("Reset headers to empty dictionary")

    return fixed, fixes
