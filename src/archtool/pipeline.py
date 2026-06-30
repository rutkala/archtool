"""Orchestrates the parse -> resolve -> validate pipeline used by the CLI."""

from __future__ import annotations

from pathlib import Path

from .errors import ArchtoolValidationError, Diagnostic
from .resolved import ResolvedModel
from .resolver import load_yaml, parse_schema, resolve
from .validation import validate_geometry


def load_and_validate(path: Path) -> tuple[ResolvedModel, list[Diagnostic]]:
    """Run schema, resolution, and geometry validation for a building file.

    Raises `ArchtoolValidationError` if any errors are found anywhere in
    the pipeline. On success, returns the resolved model plus any
    non-fatal warnings.
    """
    data = load_yaml(path)
    bf = parse_schema(data)
    model, resolution_diagnostics = resolve(bf)
    if model is None:
        raise ArchtoolValidationError(resolution_diagnostics)

    diagnostics = resolution_diagnostics + validate_geometry(model)
    if any(d.severity == "error" for d in diagnostics):
        raise ArchtoolValidationError(diagnostics)

    return model, diagnostics
