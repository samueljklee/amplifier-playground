"""Main CLI entry point for Amplifier Workbench."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import click

from amplifier_workbench.core import (
    ConfigManager,
    ModuleRegistry,
    SessionRunner,
    create_cli_event_callback,
)


# Helper to run async functions from sync Click commands
def run_async(coro):
    """Run async coroutine from sync context."""
    return asyncio.get_event_loop().run_until_complete(coro)


@click.group()
@click.version_option()
def cli():
    """Amplifier Workbench - Interactive mount plan builder and tester."""
    pass


# =============================================================================
# Module Commands
# =============================================================================


@cli.group()
def modules():
    """Manage and discover Amplifier modules."""
    pass


@modules.command("list")
@click.option("--category", "-c", help="Filter by category (orchestrator, context, provider, tool, hook)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def modules_list(category: str | None, as_json: bool):
    """List available modules."""
    registry = ModuleRegistry()

    if category:
        mods = registry.list_by_category(category)
    else:
        mods = registry.list_all()

    if as_json:
        output = [
            {
                "id": m.id,
                "name": m.name,
                "category": m.category,
                "description": m.description,
                "source": m.source,
            }
            for m in mods
        ]
        click.echo(json.dumps(output, indent=2))
    else:
        if not mods:
            click.echo("No modules found.")
            return

        # Group by category for display
        by_category: dict[str, list] = {}
        for m in mods:
            by_category.setdefault(m.category, []).append(m)

        for cat, cat_mods in sorted(by_category.items()):
            click.echo(f"\n{cat.upper()}:")
            for m in cat_mods:
                source_tag = f" [{m.source}]" if m.source != "known" else ""
                click.echo(f"  {m.id}: {m.description or m.name}{source_tag}")


@modules.command("info")
@click.argument("module_id")
def modules_info(module_id: str):
    """Show detailed info about a module."""
    registry = ModuleRegistry()
    info = registry.get_info(module_id)

    if not info:
        click.echo(f"Module not found: {module_id}", err=True)
        sys.exit(1)

    click.echo(f"ID: {info.id}")
    click.echo(f"Name: {info.name}")
    click.echo(f"Category: {info.category}")
    click.echo(f"Source: {info.source}")
    if info.description:
        click.echo(f"Description: {info.description}")
    if info.version:
        click.echo(f"Version: {info.version}")
    if info.config_schema:
        click.echo(f"Config Schema: {json.dumps(info.config_schema, indent=2)}")


@modules.command("register")
@click.argument("module_path", type=click.Path(exists=True))
@click.option("--id", "module_id", required=True, help="Module identifier")
@click.option("--name", required=True, help="Display name")
@click.option("--category", required=True, type=click.Choice(["orchestrator", "context", "provider", "tool", "hook"]))
@click.option("--description", help="Module description")
def modules_register(module_path: str, module_id: str, name: str, category: str, description: str | None):
    """Register a local development module."""
    registry = ModuleRegistry()
    registry.register_local(
        module_id=module_id,
        name=name,
        category=category,
        path=Path(module_path),
        description=description,
    )
    click.echo(f"Registered local module: {module_id}")


# =============================================================================
# Config Commands
# =============================================================================


@cli.group()
def config():
    """Manage mount plan configurations."""
    pass


@config.command("list")
@click.option("--tag", "-t", multiple=True, help="Filter by tag")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def config_list(tag: tuple[str, ...], as_json: bool):
    """List saved configurations."""
    manager = ConfigManager()
    configs = manager.list_configs(tags=list(tag) if tag else None)

    if as_json:
        output = [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "tags": c.tags,
                "created_at": c.created_at,
                "updated_at": c.updated_at,
            }
            for c in configs
        ]
        click.echo(json.dumps(output, indent=2, default=str))
    else:
        if not configs:
            click.echo("No configurations found.")
            return

        for c in configs:
            tags_str = f" [{', '.join(c.tags)}]" if c.tags else ""
            click.echo(f"  {c.id}: {c.name}{tags_str}")
            if c.description:
                click.echo(f"      {c.description}")


@config.command("show")
@click.argument("config_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def config_show(config_id: str, as_json: bool):
    """Show a configuration's details."""
    manager = ConfigManager()
    cfg = manager.get_config(config_id)

    if not cfg:
        click.echo(f"Configuration not found: {config_id}", err=True)
        sys.exit(1)

    if as_json:
        click.echo(json.dumps(cfg.__dict__, indent=2, default=str))
    else:
        click.echo(f"ID: {cfg.id}")
        click.echo(f"Name: {cfg.name}")
        if cfg.description:
            click.echo(f"Description: {cfg.description}")
        if cfg.tags:
            click.echo(f"Tags: {', '.join(cfg.tags)}")
        click.echo(f"Created: {cfg.created_at}")
        click.echo(f"Updated: {cfg.updated_at}")
        click.echo("\nMount Plan:")
        click.echo(json.dumps(cfg.mount_plan, indent=2))


@config.command("create")
@click.argument("name")
@click.option("--from-file", "-f", type=click.Path(exists=True), help="Load mount plan from JSON file")
@click.option("--from-profile", "-p", help="Load from an amplifier profile")
@click.option("--description", "-d", help="Configuration description")
@click.option("--tag", "-t", multiple=True, help="Add tags")
def config_create(
    name: str, from_file: str | None, from_profile: str | None, description: str | None, tag: tuple[str, ...]
):
    """Create a new configuration."""
    manager = ConfigManager()

    mount_plan: dict[str, Any] = {}

    if from_file:
        with open(from_file) as f:
            mount_plan = json.load(f)
    elif from_profile:
        # Load from amplifier profile
        try:
            from amplifier_profiles import load_profile  # type: ignore[import-not-found]
            mount_plan = load_profile(from_profile)
        except ImportError:
            click.echo("amplifier-profiles not installed", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"Failed to load profile: {e}", err=True)
            sys.exit(1)
    else:
        # Create minimal empty mount plan
        mount_plan = {
            "session": {
                "orchestrator": None,
                "context": None,
            },
            "providers": [],
            "tools": [],
            "hooks": [],
        }

    cfg = manager.create_config(
        name=name,
        mount_plan=mount_plan,
        description=description,
        tags=list(tag) if tag else None,
    )

    click.echo(f"Created configuration: {cfg.id}")


@config.command("delete")
@click.argument("config_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
def config_delete(config_id: str, force: bool):
    """Delete a configuration."""
    manager = ConfigManager()

    if not manager.get_config(config_id):
        click.echo(f"Configuration not found: {config_id}", err=True)
        sys.exit(1)

    if not force:
        click.confirm(f"Delete configuration '{config_id}'?", abort=True)

    manager.delete_config(config_id)
    click.echo(f"Deleted: {config_id}")


@config.command("export")
@click.argument("config_id")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def config_export(config_id: str, output: str | None):
    """Export a configuration as JSON."""
    manager = ConfigManager()
    cfg = manager.get_config(config_id)

    if not cfg:
        click.echo(f"Configuration not found: {config_id}", err=True)
        sys.exit(1)

    json_str = json.dumps(cfg.mount_plan, indent=2)

    if output:
        Path(output).write_text(json_str)
        click.echo(f"Exported to: {output}")
    else:
        click.echo(json_str)


# =============================================================================
# Session Commands
# =============================================================================


@cli.group()
def session():
    """Run and interact with Amplifier sessions."""
    pass


@session.command("run")
@click.argument("config_id")
@click.option("--prompt", "-p", help="Initial prompt to send")
@click.option("--interactive", "-i", is_flag=True, help="Enter interactive mode")
@click.option("--events", "-e", is_flag=True, help="Stream events as JSONL")
@click.option("--approval", type=click.Choice(["auto", "deny", "queue"]), default="auto", help="Approval mode")
@click.option(
    "--modules-dir",
    "-m",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    multiple=True,
    help="Directory containing amplifier modules. Can be specified multiple times.",
)
def session_run(config_id: str, prompt: str | None, interactive: bool, events: bool, approval: str, modules_dir: tuple[str, ...]):
    """Run a session with a configuration."""
    manager = ConfigManager()
    cfg = manager.get_config(config_id)

    if not cfg:
        click.echo(f"Configuration not found: {config_id}", err=True)
        sys.exit(1)

    async def run_session():
        event_callback = create_cli_event_callback() if events else None

        async with SessionRunner(
            mount_plan=cfg.mount_plan,
            event_callback=event_callback,
            approval_mode=approval,  # type: ignore
            modules_dirs=list(modules_dir) if modules_dir else None,
        ) as runner:
            click.echo(f"Session started: {runner.session_id}", err=True)

            if prompt:
                response = await runner.prompt(prompt)
                click.echo(response)

            if interactive:
                click.echo("Interactive mode. Type 'quit' to exit.", err=True)
                while True:
                    try:
                        user_input = click.prompt(">>> ", prompt_suffix="")
                        if user_input.lower() in ("quit", "exit", "q"):
                            break
                        response = await runner.prompt(user_input)
                        click.echo(response)
                    except (KeyboardInterrupt, EOFError):
                        break

            click.echo("Session ended.", err=True)

    run_async(run_session())


@session.command("test")
@click.argument("mount_plan_file", type=click.Path(exists=True))
@click.option("--prompt", "-p", required=True, help="Test prompt")
@click.option("--events", "-e", is_flag=True, help="Stream events as JSONL")
@click.option(
    "--modules-dir",
    "-m",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    multiple=True,
    help="Directory containing amplifier modules. Can be specified multiple times.",
)
def session_test(mount_plan_file: str, prompt: str, events: bool, modules_dir: tuple[str, ...]):
    """Quick test a mount plan file without saving."""
    with open(mount_plan_file) as f:
        mount_plan = json.load(f)

    async def run_test():
        event_callback = create_cli_event_callback() if events else None

        async with SessionRunner(
            mount_plan=mount_plan,
            event_callback=event_callback,
            approval_mode="auto",
            modules_dirs=list(modules_dir) if modules_dir else None,
        ) as runner:
            click.echo(f"Testing with session: {runner.session_id}", err=True)
            response = await runner.prompt(prompt)
            click.echo(response)

    run_async(run_test())


# =============================================================================
# Entry Point
# =============================================================================


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
