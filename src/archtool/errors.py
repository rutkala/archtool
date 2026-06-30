"""Diagnostics shared by schema, resolution, and geometry validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class Diagnostic:
    """A single validation finding, always naming the offending element."""

    severity: Severity
    element: str
    message: str

    def __str__(self) -> str:
        return f"{self.element}: {self.message}"


class ArchtoolValidationError(Exception):
    """Raised when a building file fails validation.

    Carries the full list of diagnostics (errors and warnings) collected
    across the schema, resolution, and geometry layers.
    """

    def __init__(self, diagnostics: list[Diagnostic]) -> None:
        self.diagnostics = diagnostics
        super().__init__("\n".join(str(d) for d in diagnostics))
