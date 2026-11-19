"""The rb-gate Typer app: `gate check` and the global `--project` option.

The console script `rb-gate` (pyproject.toml [project.scripts]) calls main(). Only argument
handling lives here; the gate itself is gate.py.
"""

from __future__ import annotations

from pathlib import Path

import typer

from .gate import Gate, NotAPackage

EXIT_USAGE = 2

app = typer.Typer(help="rb-gate — the release gate of the CLI standard")


@app.callback()
def main_options(
    ctx: typer.Context,
    project: str = typer.Option(None, "--project", help="Path to the package root (default: the current directory)."),
) -> None:
    ctx.ensure_object(dict)
    ctx.obj["project"] = project


@app.command()
def check(
    ctx: typer.Context,
    keep_going: bool = typer.Option(
        False,
        "--keep-going",
        help="Run every step and list all failed steps at the end. Use it for the first run on an old package.",
    ),
) -> None:
    """Run the release gate against the package in the current directory or `--project`.

    The steps run in order, read from the package's own pyproject.toml. Each
    step prints `release: <step> ... ok`; the first failure stops the gate
    with its output on stderr. With `--keep-going` every step runs (a step that
    needs a failed step is skipped); the failed and skipped steps are listed
    at the end. The last line and the exit code give the
    verdict: `release: gate passed` (0), `release: code failed` (1),
    `release: audit failed` (3). No pyproject.toml there: exit 2.

    Example: gate check
    Example: gate check --keep-going
    """
    try:
        gate = Gate.at(Path(ctx.obj.get("project") or Path.cwd()))
    except NotAPackage as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(EXIT_USAGE) from exc
    raise typer.Exit(gate.run_steps(typer.echo, keep_going))


def main() -> None:
    app()
