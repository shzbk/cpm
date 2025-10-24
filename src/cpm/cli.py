"""
CPM CLI - Main entry point

Matches specification from COMMANDS.md:
- Registers all command modules
- Supports --version flag
- Provides context to subcommands
"""

import sys

import click

from cpm import __version__


def print_npm_style_help():
    """Print npm-style help output"""
    help_text = """cpm <command>

Usage:

cpm install        install all the dependencies in your project
cpm install <foo>  add the <foo> dependency to your project
cpm run <foo>      run the server named <foo>
cpm add <foo>      add server to MCP clients
cpm <command> -h   quick help on <command>

All commands:

    add, cache, clients, config, group, info, init, install,
    link, ls, outdated, remove, reset, run, search, serve,
    settings, sync, uninstall, unlink, update, upgrade, version

Context files:
    Global: ~/.config/cpm/servers.json
    Local:  ./server.json (auto-detected)

Global flags:
    -h, --help     Show this help message
    -v, --version  Show CPM version
    -l, --local    Force local context (needs server.json)
    -g, --global   Force global context (ignore server.json)

More info: https://github.com/yourusername/cpm

cpm@{version}
""".format(version=__version__)

    print(help_text)


@click.group(invoke_without_command=True, add_help_option=False)
@click.option("--help", "-h", is_flag=True, help="Show this message and exit")
@click.option("--version", "-v", is_flag=True, help="Show version and exit")
@click.option("--local", "-l", is_flag=True, help="Use local project context (server.json)")
@click.option("--global", "-g", "global_flag", is_flag=True, help="Force global context")
@click.pass_context
def main(ctx, help, version, local, global_flag):
    """
    CPM - Context Protocol Manager

    The npm for MCP servers. Install, manage, and run MCP servers with ease.

    Examples:

        \b
        # Install servers
        cpm install mysql                           # Install globally
        cpm install mysql --local                   # Install to project

        \b
        # Run servers
        cpm run mysql                               # Run single server
        cpm run @database --http                    # Run group as HTTP

        \b
        # Manage clients
        cpm add mysql --to claude                   # Add to client
        cpm sync --to all                           # Sync all servers

        \b
        # Groups
        cpm group create database                   # Create group
        cpm group add database mysql postgres       # Add servers
    """
    # Store context flags for subcommands
    ctx.ensure_object(dict)
    ctx.obj["local"] = local
    ctx.obj["global"] = global_flag

    if help:
        # Show npm-style help
        print_npm_style_help()
        sys.exit(0)

    if version:
        # npm-style version output - just the version number
        print(__version__)
        sys.exit(0)

    # If no subcommand was invoked, show npm-style help
    if ctx.invoked_subcommand is None:
        print_npm_style_help()
        sys.exit(0)


# ============================================================================
# A. SERVER LIFECYCLE COMMANDS
# ============================================================================

from cpm.commands import install, uninstall, config, ls, info, search, run, serve, validate

main.add_command(install.install)
main.add_command(uninstall.uninstall)
main.add_command(config.config)
main.add_command(ls.list_servers, name="ls")
main.add_command(ls.list_servers, name="list")  # Alias for ls
main.add_command(info.info)
main.add_command(search.search)
main.add_command(run.run)
main.add_command(serve.serve)
main.add_command(validate.validate)


# ============================================================================
# B. CLIENT OPERATIONS COMMANDS
# ============================================================================

from cpm.commands import add, remove, sync, reset, clients

main.add_command(add.add)
main.add_command(remove.remove)
main.add_command(sync.sync)
main.add_command(reset.reset)
main.add_command(clients.clients)


# ============================================================================
# C. GROUP OPERATIONS COMMANDS
# ============================================================================

from cpm.commands import group

main.add_command(group.group)


# ============================================================================
# D. DEVELOPER COMMANDS
# ============================================================================

from cpm.commands import init, update, outdated, link, unlink

main.add_command(init.init)
main.add_command(update.update)
main.add_command(outdated.outdated)
main.add_command(link.link)
main.add_command(unlink.unlink)


# ============================================================================
# E. UTILITY COMMANDS
# ============================================================================

from cpm.commands import cache, settings, upgrade, version

main.add_command(cache.cache)
main.add_command(settings.settings)
main.add_command(upgrade.upgrade)
main.add_command(version.version)


# ============================================================================
# F. LEGACY COMMAND SUPPORT (for backwards compatibility)
# ============================================================================

# Support old command names if needed
# main.add_command(ls.list_servers, name="list")


if __name__ == "__main__":
    main()
