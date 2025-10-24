"""
Interactive prompt utilities using questionary
"""

from typing import Any, Dict, List, Optional

try:
    import questionary
    from questionary import Style

    HAS_QUESTIONARY = True
except ImportError:
    HAS_QUESTIONARY = False

import click


# Custom style for prompts
CUSTOM_STYLE = Style([
    ('qmark', 'fg:#673ab7 bold'),
    ('question', 'bold'),
    ('answer', 'fg:#2196f3 bold'),
    ('pointer', 'fg:#673ab7 bold'),
    ('highlighted', 'fg:#673ab7 bold'),
    ('selected', 'fg:#2196f3'),
    ('separator', 'fg:#cc5454'),
    ('instruction', ''),
    ('text', ''),
    ('disabled', 'fg:#858585 italic')
])


def prompt_text(
    message: str,
    default: Optional[str] = None,
    validate: Optional[callable] = None,
) -> str:
    """
    Prompt for text input

    Args:
        message: Prompt message
        default: Default value
        validate: Validation function

    Returns:
        User input string
    """
    if HAS_QUESTIONARY:
        return questionary.text(
            message,
            default=default or "",
            validate=validate,
            style=CUSTOM_STYLE,
        ).ask()
    else:
        # Fallback to click
        return click.prompt(message, default=default or "")


def prompt_confirm(
    message: str,
    default: bool = True,
) -> bool:
    """
    Prompt for yes/no confirmation

    Args:
        message: Prompt message
        default: Default value

    Returns:
        True if confirmed, False otherwise
    """
    if HAS_QUESTIONARY:
        return questionary.confirm(
            message,
            default=default,
            style=CUSTOM_STYLE,
        ).ask()
    else:
        # Fallback to click
        return click.confirm(message, default=default)


def prompt_select(
    message: str,
    choices: List[str],
    default: Optional[str] = None,
) -> str:
    """
    Prompt for single selection from list

    Args:
        message: Prompt message
        choices: List of choices
        default: Default choice

    Returns:
        Selected choice
    """
    if HAS_QUESTIONARY:
        return questionary.select(
            message,
            choices=choices,
            default=default,
            style=CUSTOM_STYLE,
        ).ask()
    else:
        # Fallback to click
        for i, choice in enumerate(choices, 1):
            click.echo(f"{i}. {choice}")

        while True:
            try:
                idx = click.prompt("Select", type=int, default=1)
                if 1 <= idx <= len(choices):
                    return choices[idx - 1]
                else:
                    click.echo(f"Please enter a number between 1 and {len(choices)}")
            except (ValueError, click.Abort):
                return choices[0] if default is None else default


def prompt_checkbox(
    message: str,
    choices: List[str],
    default: Optional[List[str]] = None,
) -> List[str]:
    """
    Prompt for multiple selections from list

    Args:
        message: Prompt message
        choices: List of choices
        default: Default selections

    Returns:
        List of selected choices
    """
    if HAS_QUESTIONARY:
        return questionary.checkbox(
            message,
            choices=choices,
            default=default or [],
            style=CUSTOM_STYLE,
        ).ask()
    else:
        # Fallback to click (simplified - select all by default)
        click.echo(message)
        for choice in choices:
            click.echo(f"  - {choice}")

        if click.confirm("Use all?", default=True):
            return choices
        else:
            return default or []


def prompt_autocomplete(
    message: str,
    choices: List[str],
    default: Optional[str] = None,
) -> str:
    """
    Prompt with autocomplete

    Args:
        message: Prompt message
        choices: List of choices for autocomplete
        default: Default value

    Returns:
        User input string
    """
    if HAS_QUESTIONARY:
        return questionary.autocomplete(
            message,
            choices=choices,
            default=default or "",
            style=CUSTOM_STYLE,
        ).ask()
    else:
        # Fallback to select
        return prompt_select(message, choices, default)


def prompt_password(
    message: str,
) -> str:
    """
    Prompt for password (hidden input)

    Args:
        message: Prompt message

    Returns:
        Password string
    """
    if HAS_QUESTIONARY:
        return questionary.password(
            message,
            style=CUSTOM_STYLE,
        ).ask()
    else:
        # Fallback to click
        return click.prompt(message, hide_input=True)


def prompt_path(
    message: str,
    default: Optional[str] = None,
    only_directories: bool = False,
) -> str:
    """
    Prompt for file/directory path

    Args:
        message: Prompt message
        default: Default path
        only_directories: Only allow directories

    Returns:
        Path string
    """
    if HAS_QUESTIONARY:
        return questionary.path(
            message,
            default=default or "",
            only_directories=only_directories,
            style=CUSTOM_STYLE,
        ).ask()
    else:
        # Fallback to text
        return prompt_text(message, default)


def prompt_project_init() -> Dict[str, Any]:
    """
    Interactive wizard for project initialization

    Returns:
        Dictionary with project configuration
    """
    from pathlib import Path

    config = {}

    # Project name
    default_name = Path.cwd().name
    config["name"] = prompt_text(
        "Project name:",
        default=default_name,
    )

    # Version
    config["version"] = prompt_text(
        "Version:",
        default="1.0.0",
    )

    # Template
    templates = ["basic", "ai-agent"]
    config["template"] = prompt_select(
        "Select template:",
        choices=templates,
        default="basic",
    )

    return config


def prompt_server_config() -> Dict[str, Any]:
    """
    Interactive wizard for server configuration

    Returns:
        Dictionary with server configuration
    """
    config = {}

    # Server type
    server_type = prompt_select(
        "Server type:",
        choices=["stdio", "remote"],
        default="stdio",
    )

    config["type"] = server_type

    # Server name
    config["name"] = prompt_text(
        "Server name:",
    )

    if server_type == "stdio":
        # STDIO configuration
        config["command"] = prompt_text(
            "Command:",
            default="node",
        )

        args_str = prompt_text(
            "Arguments (space-separated):",
            default="",
        )

        if args_str:
            config["args"] = args_str.split()
        else:
            config["args"] = []

        # Environment variables
        if prompt_confirm("Add environment variables?", default=False):
            config["env"] = {}

            while True:
                key = prompt_text("Variable name (empty to finish):")
                if not key:
                    break

                value = prompt_text(f"Value for {key}:")
                config["env"][key] = value

    else:
        # Remote configuration
        config["url"] = prompt_text(
            "Server URL:",
            default="https://",
        )

        # Headers
        if prompt_confirm("Add custom headers?", default=False):
            config["headers"] = {}

            while True:
                key = prompt_text("Header name (empty to finish):")
                if not key:
                    break

                value = prompt_text(f"Value for {key}:")
                config["headers"][key] = value

    return config


def prompt_add_clients(detected_clients: List[str]) -> List[str]:
    """
    Prompt to select clients to add servers to

    Args:
        detected_clients: List of detected client names

    Returns:
        List of selected client names
    """
    if not detected_clients:
        return []

    # Add "All" option
    choices = ["all"] + detected_clients

    selection = prompt_select(
        "Add to which client(s)?",
        choices=choices,
        default="all",
    )

    if selection == "all":
        return detected_clients
    else:
        return [selection]


def prompt_env_var() -> tuple[str, str]:
    """
    Prompt for environment variable key=value

    Returns:
        Tuple of (key, value)
    """
    key = prompt_text(
        "Environment variable name:",
    )

    value = prompt_text(
        f"Value for {key}:",
    )

    return key, value


def prompt_confirmation(
    message: str,
    items: List[str],
    default: bool = True,
) -> bool:
    """
    Show confirmation prompt with list of items

    Args:
        message: Confirmation message
        items: List of items to show
        default: Default confirmation value

    Returns:
        True if confirmed
    """
    from rich.console import Console

    console = Console()

    console.print(f"\n[cyan]{message}[/]\n")

    for item in items:
        console.print(f"  • {item}")

    console.print()

    return prompt_confirm("Continue?", default=default)
