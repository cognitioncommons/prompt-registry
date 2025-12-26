"""CLI for prompt-registry - manage version-controlled prompt templates."""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich import box

from .registry import PromptRegistry


console = Console()
error_console = Console(stderr=True)


def get_prompts_dir() -> Path:
    """Get the prompts directory path."""
    return Path.cwd() / "prompts"


@click.group()
@click.option(
    "--prompts-dir",
    "-d",
    type=click.Path(path_type=Path),
    default=None,
    help="Directory containing prompt templates (default: ./prompts)",
)
@click.pass_context
def cli(ctx: click.Context, prompts_dir: Optional[Path]) -> None:
    """Prompt Registry - Version-controlled prompt templates with variables."""
    ctx.ensure_object(dict)
    ctx.obj["prompts_dir"] = prompts_dir or get_prompts_dir()


@cli.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Initialize the prompts directory with an example template."""
    prompts_dir = ctx.obj["prompts_dir"]
    registry = PromptRegistry(prompts_dir)

    try:
        path = registry.init_prompts_dir()
        console.print(f"[green]Initialized prompts directory at:[/green] {path}")
        console.print("[dim]Created example.yaml template[/dim]")
    except Exception as e:
        error_console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command("list")
@click.pass_context
def list_prompts(ctx: click.Context) -> None:
    """List all available prompt templates."""
    prompts_dir = ctx.obj["prompts_dir"]
    registry = PromptRegistry(prompts_dir)

    try:
        registry.load()
    except ValueError as e:
        error_console.print(f"[red]Error loading prompts:[/red] {e}")
        sys.exit(1)

    prompts = registry.list_prompts()

    if not prompts:
        console.print("[yellow]No prompts found.[/yellow]")
        console.print(f"[dim]Looking in: {prompts_dir}[/dim]")
        console.print("[dim]Run 'prompt-registry init' to create an example.[/dim]")
        return

    table = Table(title="Prompt Templates", box=box.ROUNDED)
    table.add_column("Name", style="cyan")
    table.add_column("Versions", style="magenta")
    table.add_column("Description", style="dim")

    for name in prompts:
        versions = registry.list_versions(name)
        latest = registry.get(name)
        desc = latest.description if latest else ""
        version_str = ", ".join(f"v{v}" for v in versions)
        table.add_row(name, version_str, desc[:50] + "..." if len(desc) > 50 else desc)

    console.print(table)


@cli.command()
@click.argument("name")
@click.option("--version", "-v", type=int, default=None, help="Specific version to show")
@click.pass_context
def show(ctx: click.Context, name: str, version: Optional[int]) -> None:
    """Show details of a specific prompt template."""
    prompts_dir = ctx.obj["prompts_dir"]
    registry = PromptRegistry(prompts_dir)

    try:
        registry.load()
    except ValueError as e:
        error_console.print(f"[red]Error loading prompts:[/red] {e}")
        sys.exit(1)

    template = registry.get(name, version)

    if template is None:
        error_console.print(f"[red]Template '{name}' not found.[/red]")
        sys.exit(1)

    # Header
    console.print(
        Panel(
            f"[bold cyan]{template.name}[/bold cyan] v{template.version}",
            subtitle=template.description or "No description",
        )
    )

    # Variables section
    if template.variables:
        var_table = Table(title="Variables", box=box.SIMPLE)
        var_table.add_column("Name", style="cyan")
        var_table.add_column("Required", style="yellow")
        var_table.add_column("Default", style="green")
        var_table.add_column("Description", style="dim")

        for var_name, var_spec in template.variables.items():
            req = "Yes" if var_spec.required else "No"
            default = str(var_spec.default) if var_spec.default is not None else "-"
            var_table.add_row(var_name, req, default, var_spec.description)

        console.print(var_table)
    else:
        console.print("[dim]No variables defined[/dim]")

    # Template section
    console.print("\n[bold]Template:[/bold]")
    syntax = Syntax(template.template, "jinja2", theme="monokai", line_numbers=True)
    console.print(syntax)


@cli.command()
@click.argument("name")
@click.option("--version", "-v", type=int, default=None, help="Specific version to use")
@click.option("--var", "-V", multiple=True, help="Variable in key=value format")
@click.pass_context
def render(ctx: click.Context, name: str, version: Optional[int], var: tuple) -> None:
    """Render a prompt template with variables."""
    prompts_dir = ctx.obj["prompts_dir"]
    registry = PromptRegistry(prompts_dir)

    try:
        registry.load()
    except ValueError as e:
        error_console.print(f"[red]Error loading prompts:[/red] {e}")
        sys.exit(1)

    template = registry.get(name, version)

    if template is None:
        error_console.print(f"[red]Template '{name}' not found.[/red]")
        sys.exit(1)

    # Parse variables
    variables = {}
    for v in var:
        if "=" not in v:
            error_console.print(f"[red]Invalid variable format '{v}'. Use key=value.[/red]")
            sys.exit(1)
        key, value = v.split("=", 1)
        variables[key] = value

    # Check for missing required variables
    missing = [
        v for v in template.get_required_variables() if v not in variables
    ]
    if missing:
        error_console.print(f"[red]Missing required variables:[/red] {', '.join(missing)}")
        console.print("\n[dim]Use --var key=value to provide variables[/dim]")
        sys.exit(1)

    try:
        rendered = template.render(**variables)
        console.print(Panel(rendered, title=f"Rendered: {name} v{template.version}"))
    except ValueError as e:
        error_console.print(f"[red]Error rendering template:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def validate(ctx: click.Context) -> None:
    """Validate all prompt templates."""
    prompts_dir = ctx.obj["prompts_dir"]
    registry = PromptRegistry(prompts_dir)

    try:
        registry.load()
    except ValueError as e:
        error_console.print(f"[red]Error loading prompts:[/red] {e}")
        sys.exit(1)

    prompts = registry.list_prompts()

    if not prompts:
        console.print("[yellow]No prompts found to validate.[/yellow]")
        return

    errors = registry.validate_all()

    if not errors:
        console.print(f"[green]All {len(prompts)} prompt(s) validated successfully.[/green]")
        return

    # Show errors
    console.print(f"[red]Validation errors found:[/red]")
    for template_key, template_errors in errors.items():
        console.print(f"\n[yellow]{template_key}:[/yellow]")
        for error in template_errors:
            console.print(f"  [red]- {error}[/red]")

    sys.exit(1)


@cli.command()
@click.argument("name")
@click.option("--description", "-d", default="", help="Prompt description")
@click.option("--var", "-V", multiple=True, help="Variable in name:description format (use ! suffix for required)")
@click.pass_context
def new(ctx: click.Context, name: str, description: str, var: tuple) -> None:
    """Create a new prompt template."""
    prompts_dir = ctx.obj["prompts_dir"]
    registry = PromptRegistry(prompts_dir)

    # Check if prompt already exists
    registry.load()
    if name in registry:
        error_console.print(f"[red]Template '{name}' already exists.[/red]")
        sys.exit(1)

    # Parse variables
    variables = {}
    template_vars = []

    for v in var:
        if ":" in v:
            var_name, var_desc = v.split(":", 1)
        else:
            var_name = v
            var_desc = ""

        # Check for required marker
        required = True
        if var_name.endswith("!"):
            var_name = var_name[:-1]
            required = True
        elif var_name.endswith("?"):
            var_name = var_name[:-1]
            required = False

        variables[var_name] = {
            "required": required,
            "description": var_desc,
        }
        template_vars.append(f"{{{{ {var_name} }}}}")

    # Create a placeholder template
    if template_vars:
        template_text = "Your prompt here.\n\n" + "\n".join(template_vars) + "\n"
    else:
        template_text = "Your prompt template here.\n"

    try:
        path = registry.create_prompt(
            name=name,
            template=template_text,
            description=description,
            variables=variables,
        )
        console.print(f"[green]Created new prompt template:[/green] {path}")
        console.print("[dim]Edit the file to customize your template.[/dim]")
    except Exception as e:
        error_console.print(f"[red]Error creating template:[/red] {e}")
        sys.exit(1)


def main() -> None:
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
