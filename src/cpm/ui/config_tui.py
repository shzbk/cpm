"""
Textual TUI for server configuration
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.widgets import Button, Input, Label, Static
from textual.binding import Binding


class RequiredValidator(Validator):
    """Validator that checks if a value is required"""

    def __init__(self, required: bool = False):
        super().__init__()
        self.required = required

    def validate(self, value: str) -> ValidationResult:
        """Check if value is provided when required"""
        if self.required and not value:
            return self.failure("This field is required")
        return self.success()


class ConfigField(Container):
    """A configuration field with label and input"""

    DEFAULT_CSS = """
    ConfigField {
        height: auto;
        margin: 1 2;
        padding: 0;
    }

    ConfigField Label {
        color: $accent;
        margin-bottom: 1;
    }

    ConfigField .required {
        color: $error;
    }

    ConfigField .configured {
        color: $success;
    }

    ConfigField Input {
        margin-bottom: 1;
    }
    """

    def __init__(
        self,
        var_name: str,
        current_value: str,
        is_placeholder: bool,
        is_password: bool = False,
    ):
        super().__init__()
        self.var_name = var_name
        self.current_value = current_value
        self.is_placeholder = is_placeholder
        self.is_password = is_password

    def compose(self) -> ComposeResult:
        """Create the field UI"""
        status = "required" if self.is_placeholder else "configured"
        status_text = "(required)" if self.is_placeholder else "(configured)"

        yield Label(f"{self.var_name} ", classes=status)
        yield Static(status_text, classes=status)

        default_value = "" if self.is_placeholder else self.current_value

        yield Input(
            value=default_value,
            placeholder=f"Enter {self.var_name}",
            password=self.is_password,
            validators=[RequiredValidator(required=self.is_placeholder)],
            id=f"input_{self.var_name}",
        )


class ConfigScreen(ModalScreen[dict | None]):
    """Modal screen for configuration"""

    CSS = """
    ConfigScreen {
        align: center middle;
    }

    #config_dialog {
        width: 60;
        height: auto;
        max-height: 90%;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
    }

    #title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $accent;
        padding: 1;
        background: $primary;
    }

    #fields_container {
        width: 100%;
        height: auto;
        overflow-y: auto;
        margin: 1 0;
    }

    #buttons {
        width: 100%;
        height: auto;
        align: center middle;
        padding: 1;
    }

    #buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, server_name: str, env_vars: dict):
        super().__init__()
        self.server_name = server_name
        self.env_vars = env_vars

    def compose(self) -> ComposeResult:
        """Create the configuration dialog"""
        with Container(id="config_dialog"):
            yield Static(f"{self.server_name} Configuration", id="title")

            with Vertical(id="fields_container"):
                for var_name, value in self.env_vars.items():
                    is_placeholder = isinstance(value, str) and value.startswith("${") and value.endswith("}")
                    is_password = any(
                        keyword in var_name.lower() for keyword in ["password", "secret", "token", "key"]
                    )

                    yield ConfigField(var_name, value, is_placeholder, is_password)

            with Container(id="buttons"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="default", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "save":
            # Collect all values
            new_env = {}
            for var_name in self.env_vars.keys():
                input_widget = self.query_one(f"#input_{var_name}", Input)
                value = input_widget.value.strip()

                # Validate required fields
                if not value:
                    # Check if it was required (placeholder)
                    old_value = self.env_vars[var_name]
                    if isinstance(old_value, str) and old_value.startswith("${"):
                        # Required field is empty, don't save
                        input_widget.focus()
                        return

                # Use new value or keep old value if empty
                if value:
                    new_env[var_name] = value
                else:
                    new_env[var_name] = self.env_vars[var_name]

            self.dismiss(new_env)
        elif event.button.id == "cancel":
            self.dismiss(None)


class ConfigApp(App):
    """Main Textual app for configuration"""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    CSS = """
    Screen {
        background: $surface;
    }
    """

    def __init__(self, server_name: str, env_vars: dict):
        super().__init__()
        self.server_name = server_name
        self.env_vars = env_vars
        self.result = None

    def compose(self) -> ComposeResult:
        """Create app UI"""
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        """When app mounts, show the config screen"""
        self.push_screen(ConfigScreen(self.server_name, self.env_vars), callback=self._handle_result)

    def _handle_result(self, result: dict | None) -> None:
        """Handle the result from the config screen"""
        self.result = result
        self.exit()

    def action_cancel(self) -> None:
        """Cancel configuration"""
        self.result = None
        self.exit()


def run_config_tui(server_name: str, env_vars: dict) -> dict | None:
    """Run the configuration TUI and return the result"""
    app = ConfigApp(server_name, env_vars)
    app.run()
    return app.result
