"""Main CLI entry point for Amplifier Workbench."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import click

from amplifier_workbench.core import (
    CollectionManager,
    ConfigManager,
    ModuleRegistry,
    SessionRunner,
    create_cli_event_callback,
)
from amplifier_workbench.core.mention_loader import MentionLoader, MentionResolver
from amplifier_profiles import (
    ProfileLoader,
    ProfileError,
    compile_profile_to_mount_plan,
    AgentLoader,
    AgentResolver,
)


class CollectionResolverAdapter:
    """Adapter to make CollectionManager work with ProfileLoader and AgentResolver."""

    def __init__(self, collection_manager: CollectionManager):
        self._manager = collection_manager

    def resolve(self, collection_name: str) -> Path | None:
        """Resolve collection name to filesystem path."""
        return self._manager.resolve_collection(collection_name)


def build_agent_loader(collection_manager: CollectionManager) -> AgentLoader:
    """
    Build an AgentLoader with search paths from collections and local directories.

    Search order (highest priority first):
    1. Project-local: ./.amplifier/agents/
    2. User-global: ~/.amplifier/agents/
    3. Collection agents directories
    """
    search_paths: list[Path] = []
    resolver_adapter = CollectionResolverAdapter(collection_manager)

    # Local agents directories (will be searched in reverse order = highest priority)
    local_agents = Path.cwd() / ".amplifier" / "agents"
    if local_agents.exists():
        search_paths.append(local_agents)

    user_agents = Path.home() / ".amplifier" / "agents"
    if user_agents.exists():
        search_paths.append(user_agents)

    # Collection agents directories
    # The resolver returns the package dir, agents are at parent/agents
    for coll in collection_manager.list_collections():
        coll_path = collection_manager.resolve_collection(coll.name)
        if coll_path:
            # Hybrid packaging: agents are at collection root, not in package
            agents_path = coll_path.parent / "agents"
            if agents_path.exists():
                search_paths.append(agents_path)

    # Create resolver and loader
    agent_resolver = AgentResolver(
        search_paths=search_paths,
        collection_resolver=resolver_adapter,
    )

    # Create mention loader for @mention expansion in agent markdown
    mention_resolver = MentionResolver(collection_manager=collection_manager)
    mention_loader = MentionLoader(resolver=mention_resolver)

    return AgentLoader(resolver=agent_resolver, mention_loader=mention_loader)


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
# Collection Commands
# =============================================================================


@cli.group()
def collections():
    """Discover and browse collections."""
    pass


@collections.command("list")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def collections_list(as_json: bool):
    """List available collections."""
    manager = CollectionManager()
    colls = manager.list_collections()

    if as_json:
        output = [{"name": c.name, "path": str(c.path)} for c in colls]
        click.echo(json.dumps(output, indent=2))
    else:
        if not colls:
            click.echo("No collections found.")
            click.echo("\nSearch paths:")
            for p in manager.search_paths:
                click.echo(f"  {p}")
            return

        click.echo("Available collections:")
        for c in colls:
            click.echo(f"  {c.name}: {c.path}")


@collections.command("show")
@click.argument("collection_name")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def collections_show(collection_name: str, as_json: bool):
    """Show details about a collection."""
    manager = CollectionManager()
    info = manager.get_collection_info(collection_name)

    if not info:
        click.echo(f"Collection not found: {collection_name}", err=True)
        sys.exit(1)

    if as_json:
        output = {
            "name": info.name,
            "path": str(info.path),
            "resources": {
                "profiles": [str(p) for p in (info.resources.profiles if info.resources else [])],
                "agents": [str(p) for p in (info.resources.agents if info.resources else [])],
                "context": [str(p) for p in (info.resources.context if info.resources else [])],
                "scenario_tools": [str(p) for p in (info.resources.scenario_tools if info.resources else [])],
                "modules": [str(p) for p in (info.resources.modules if info.resources else [])],
            },
        }
        click.echo(json.dumps(output, indent=2))
    else:
        click.echo(f"Collection: {info.name}")
        click.echo(f"Path: {info.path}")

        if info.resources:
            if info.resources.profiles:
                click.echo(f"\nProfiles ({len(info.resources.profiles)}):")
                for p in info.resources.profiles:
                    click.echo(f"  {p.name}")

            if info.resources.agents:
                click.echo(f"\nAgents ({len(info.resources.agents)}):")
                for a in info.resources.agents:
                    click.echo(f"  {a.name}")

            if info.resources.context:
                click.echo(f"\nContext ({len(info.resources.context)}):")
                for c in info.resources.context:
                    click.echo(f"  {c.name}")

            if info.resources.scenario_tools:
                click.echo(f"\nScenario Tools ({len(info.resources.scenario_tools)}):")
                for s in info.resources.scenario_tools:
                    click.echo(f"  {s.name}")

            if info.resources.modules:
                click.echo(f"\nModules ({len(info.resources.modules)}):")
                for m in info.resources.modules:
                    click.echo(f"  {m.name}")


@collections.command("profiles")
@click.argument("collection_name")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def collections_profiles(collection_name: str, as_json: bool):
    """List profiles in a collection."""
    manager = CollectionManager()
    profiles = manager.list_profiles_in_collection(collection_name)

    if as_json:
        click.echo(json.dumps([str(p) for p in profiles], indent=2))
    else:
        if not profiles:
            click.echo(f"No profiles found in collection: {collection_name}")
            return

        click.echo(f"Profiles in {collection_name}:")
        for p in profiles:
            click.echo(f"  {p.stem}")


# =============================================================================
# Profile Commands
# =============================================================================


@cli.group()
def profiles():
    """Browse and manage profiles."""
    pass


@profiles.command("list")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def profiles_list(as_json: bool):
    """List all available profiles from collections and local directories."""
    manager = CollectionManager()

    all_profiles: list[dict[str, Any]] = []

    # Get profiles from each collection
    for coll in manager.list_collections():
        coll_profiles = manager.list_profiles_in_collection(coll.name)
        for p in coll_profiles:
            all_profiles.append({
                "name": f"{coll.name}:{p.stem}",
                "collection": coll.name,
                "profile": p.stem,
                "path": str(p),
            })

    # Get local profiles
    local_paths = [
        Path.cwd() / ".amplifier" / "profiles",
        Path.home() / ".amplifier" / "profiles",
    ]

    for local_path in local_paths:
        if local_path.exists():
            for p in local_path.glob("*.md"):
                all_profiles.append({
                    "name": p.stem,
                    "collection": None,
                    "profile": p.stem,
                    "path": str(p),
                })

    if as_json:
        click.echo(json.dumps(all_profiles, indent=2))
    else:
        if not all_profiles:
            click.echo("No profiles found.")
            return

        # Group by collection
        by_collection: dict[str | None, list] = {}
        for p in all_profiles:
            coll = p["collection"]
            by_collection.setdefault(coll, []).append(p)

        # Show collection profiles
        for coll, profs in sorted(by_collection.items(), key=lambda x: (x[0] is None, x[0] or "")):
            if coll:
                click.echo(f"\n{coll}:")
                for p in profs:
                    click.echo(f"  {p['profile']:<20} → awb session run {p['name']}")
            else:
                click.echo("\nLocal profiles:")
                for p in profs:
                    click.echo(f"  {p['profile']:<20} → awb session run {p['profile']}")


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
@click.option("--from-profile", "-p", help="Load from a profile (use collection:profile syntax for collections)")
@click.option("--description", "-d", help="Configuration description")
@click.option("--tag", "-t", multiple=True, help="Add tags")
def config_create(
    name: str,
    from_file: str | None,
    from_profile: str | None,
    description: str | None,
    tag: tuple[str, ...],
):
    """Create a new configuration.

    Profiles can be loaded from collections using the collection:profile syntax.
    For example: --from-profile design-intelligence:designer

    The profile will be fully compiled with inheritance resolution and module merging.
    """
    manager = ConfigManager()

    mount_plan: dict[str, Any] = {}

    if from_file:
        with open(from_file) as f:
            mount_plan = json.load(f)
    elif from_profile:
        # Load and compile profile (supports collection:profile syntax)
        try:
            coll_manager = CollectionManager()
            resolver = CollectionResolverAdapter(coll_manager)

            # Build search paths for local profiles
            local_search_paths: list[Path] = []
            local_profiles = Path.cwd() / ".amplifier" / "profiles"
            if local_profiles.exists():
                local_search_paths.append(local_profiles)
            user_profiles = Path.home() / ".amplifier" / "profiles"
            if user_profiles.exists():
                local_search_paths.append(user_profiles)

            loader = ProfileLoader(
                search_paths=local_search_paths,
                collection_resolver=resolver,
            )

            # Load profile with inheritance resolution
            profile = loader.load_profile(from_profile)

            # Build agent loader for agents: all resolution
            agent_loader = build_agent_loader(coll_manager)

            # Compile to mount plan
            mount_plan = compile_profile_to_mount_plan(profile, agent_loader=agent_loader)

            click.echo(f"Compiled profile: {profile.profile.name}", err=True)

        except ProfileError as e:
            click.echo(f"Failed to load profile: {e}", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"Failed to compile profile: {e}", err=True)
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
@click.argument("profile")
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
def session_run(
    profile: str,
    prompt: str | None,
    interactive: bool,
    events: bool,
    approval: str,
    modules_dir: tuple[str, ...],
):
    """Run a session from a profile.

    PROFILE can be:
    - A collection profile: collection:profile (e.g., 'foundation:base')
    - A local profile name from .amplifier/profiles/ or ~/.amplifier/profiles/

    Examples:
        awb session run foundation:base
        awb session run developer-expertise:dev --interactive
        awb session run my-local-profile -p "Hello world"
    """
    # Compile profile to mount plan
    try:
        coll_manager = CollectionManager()
        resolver = CollectionResolverAdapter(coll_manager)

        # Build search paths for local profiles
        local_search_paths: list[Path] = []
        local_profiles = Path.cwd() / ".amplifier" / "profiles"
        if local_profiles.exists():
            local_search_paths.append(local_profiles)
        user_profiles = Path.home() / ".amplifier" / "profiles"
        if user_profiles.exists():
            local_search_paths.append(user_profiles)

        loader = ProfileLoader(
            search_paths=local_search_paths,
            collection_resolver=resolver,
        )

        # Load profile with inheritance resolution
        loaded_profile = loader.load_profile(profile)

        # Build agent loader for agents: all resolution
        agent_loader = build_agent_loader(coll_manager)

        # Compile to mount plan
        mount_plan = compile_profile_to_mount_plan(loaded_profile, agent_loader=agent_loader)

        click.echo(f"Using profile: {loaded_profile.profile.name}", err=True)

    except ProfileError as e:
        click.echo(f"Failed to load profile '{profile}': {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Failed to compile profile '{profile}': {e}", err=True)
        sys.exit(1)

    async def run_session():
        event_callback = create_cli_event_callback() if events else None

        async with SessionRunner(
            mount_plan=mount_plan,
            event_callback=event_callback,
            approval_mode=approval,  # type: ignore
            modules_dirs=list(modules_dir) if modules_dir else None,
            profile_name=profile,
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
