"""
Manage CPM cache
"""

import click
from pathlib import Path
from rich.console import Console

from cpm.core.registry import RegistryClient

console = Console()


@click.group()
def cache():
    """
    Manage CPM cache

    Examples:

        \b
        cpm cache clean                       # Clear cache
        cpm cache path                        # Show cache location
        cpm cache verify                      # Verify cache integrity
    """
    pass


@cache.command("clean")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation")
def cache_clean(yes):
    """
    Clear CPM cache

    Examples:

        \b
        cpm cache clean                       # Clear cache with confirmation
        cpm cache clean --yes                 # Clear without confirmation
    """
    registry = RegistryClient()

    # Get cache path
    cache_path = registry.cache_dir

    if not cache_path.exists():
        console.print("[yellow]Cache is already empty[/]")
        return

    # Count cache size
    try:
        cache_files = list(cache_path.glob("**/*"))
        cache_count = len([f for f in cache_files if f.is_file()])
        cache_size = sum(f.stat().st_size for f in cache_files if f.is_file())
        cache_size_mb = cache_size / (1024 * 1024)

        console.print(f"\n[cyan]Cache information:[/]")
        console.print(f"  [dim]Location: {cache_path}[/]")
        console.print(f"  [dim]Files: {cache_count}[/]")
        console.print(f"  [dim]Size: {cache_size_mb:.2f} MB[/]")

    except Exception as e:
        console.print(f"[yellow]Warning: Could not calculate cache size: {e}[/]")

    # Confirm
    if not yes:
        console.print()
        if not click.confirm("Clear cache?", default=True):
            console.print("[yellow]Aborted[/]")
            return

    # Clean cache
    try:
        import shutil

        shutil.rmtree(cache_path)
        cache_path.mkdir(parents=True, exist_ok=True)

        console.print(f"\n[green]+[/] Cache cleared")

    except Exception as e:
        console.print(f"\n[red]Error:[/] Failed to clear cache: {e}")
        raise click.Abort()


@cache.command("path")
def cache_path():
    """
    Show cache location

    Examples:

        \b
        cpm cache path                        # Show cache path
    """
    registry = RegistryClient()
    cache_dir = registry.cache_dir

    console.print(f"\n[cyan]Cache location:[/]")
    console.print(f"  {cache_dir}")

    # Check if cache exists
    if cache_dir.exists():
        try:
            cache_files = list(cache_dir.glob("**/*"))
            cache_count = len([f for f in cache_files if f.is_file()])
            console.print(f"\n[dim]Files: {cache_count}[/]")
        except:
            pass
    else:
        console.print("\n[dim]Cache directory does not exist[/]")

    console.print()


@cache.command("verify")
def cache_verify():
    """
    Verify cache integrity

    Examples:

        \b
        cpm cache verify                      # Verify cache
    """
    registry = RegistryClient()
    cache_dir = registry.cache_dir

    if not cache_dir.exists():
        console.print("[yellow]Cache is empty[/]")
        return

    console.print("[cyan]Verifying cache...[/]\n")

    try:
        # Check cache structure
        cache_files = list(cache_dir.glob("**/*"))
        file_count = len([f for f in cache_files if f.is_file()])

        # Basic verification
        console.print(f"[green]+[/] Cache directory exists: {cache_dir}")
        console.print(f"[green]+[/] Found {file_count} file(s)")

        # Check if readable
        readable_count = 0
        unreadable_files = []

        for file_path in cache_files:
            if file_path.is_file():
                try:
                    with open(file_path, "rb") as f:
                        f.read(1)  # Try to read first byte
                    readable_count += 1
                except Exception as e:
                    unreadable_files.append((file_path, str(e)))

        if unreadable_files:
            console.print(f"\n[yellow]Warning:[/] Found {len(unreadable_files)} unreadable file(s):")
            for file_path, error in unreadable_files[:5]:  # Show first 5
                console.print(f"  [red]-[/] {file_path.name}: {error}")

            if len(unreadable_files) > 5:
                console.print(f"  [dim]... and {len(unreadable_files) - 5} more[/]")

            console.print(f"\n[dim]Run 'cpm cache clean' to clear corrupted cache[/]")
        else:
            console.print(f"[green]+[/] All files readable ({readable_count}/{file_count})")

        console.print(f"\n[green]Cache verification complete[/]")

    except Exception as e:
        console.print(f"[red]Error:[/] Failed to verify cache: {e}")
        raise click.Abort()
