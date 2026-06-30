"""archtool CLI: `init`, `validate`, and `build`."""

from __future__ import annotations

import time
from pathlib import Path

import typer

from .backends.svg import write_svg
from .errors import ArchtoolValidationError, Diagnostic
from .pipeline import load_and_validate
from .scaffold import init_project

app = typer.Typer(add_completion=False, help="archtool: a compiler for buildings.")


def _print_diagnostics(diagnostics: list[Diagnostic]) -> None:
    for d in diagnostics:
        label = "ERROR" if d.severity == "error" else "WARNING"
        typer.echo(f"{label}: {d}", err=(d.severity == "error"))


@app.command()
def init(name: str = typer.Argument(..., help="Project name; created as a new subdirectory.")) -> None:
    """Scaffold a new building project in ./<name>/ (starter dom_dane.yaml + README)."""
    target = Path(name)
    if target.exists():
        typer.echo(f"ERROR: '{target}' already exists.", err=True)
        raise typer.Exit(code=1)
    init_project(target, name)
    typer.echo(f"Created '{target}/' with a starter dom_dane.yaml and README.md.")
    typer.echo(f"Next: cd {target} && archtool validate dom_dane.yaml")


@app.command()
def validate(
    file: Path = typer.Argument(..., exists=True, dir_okay=False, help="Path to a building YAML file."),
) -> None:
    """Validate a building file: schema checks, then geometry checks."""
    try:
        _, diagnostics = load_and_validate(file)
    except ArchtoolValidationError as exc:
        _print_diagnostics(exc.diagnostics)
        raise typer.Exit(code=1) from None
    _print_diagnostics(diagnostics)
    typer.echo(f"OK: '{file}' is valid.")


def _build_once(file: Path, out_path: Path) -> bool:
    try:
        model, diagnostics = load_and_validate(file)
    except ArchtoolValidationError as exc:
        _print_diagnostics(exc.diagnostics)
        return False
    _print_diagnostics(diagnostics)
    write_svg(model, out_path)
    typer.echo(f"Built '{out_path}'.")
    return True


@app.command()
def build(
    file: Path = typer.Argument(..., exists=True, dir_okay=False, help="Path to a building YAML file."),
    out: Path = typer.Option(None, "--out", "-o", help="Output SVG path. Defaults to the input file with .svg."),
    watch: bool = typer.Option(False, "--watch", help="Re-build whenever the input file changes."),
) -> None:
    """Validate, then render the SVG floor plan."""
    out_path = out or file.with_suffix(".svg")

    ok = _build_once(file, out_path)

    if not watch:
        if not ok:
            raise typer.Exit(code=1)
        return

    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    class _Handler(FileSystemEventHandler):
        def on_modified(self, event: object) -> None:
            src_path = getattr(event, "src_path", None)
            if src_path and Path(src_path).resolve() == file.resolve():
                typer.echo(f"Change detected in '{file}', rebuilding...")
                _build_once(file, out_path)

    observer = Observer()
    observer.schedule(_Handler(), str(file.parent), recursive=False)
    observer.start()
    typer.echo(f"Watching '{file}' for changes. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    app()
