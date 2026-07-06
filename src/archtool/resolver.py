"""Stage 1: load YAML, validate schema, resolve named points into coordinates.

Produces the canonical `ResolvedModel` (see `archtool.resolved`). This is
the only module allowed to know about point *names* — everything
downstream works in plain coordinates.
"""

from __future__ import annotations

import difflib
import itertools
import string
from pathlib import Path

import yaml
from pydantic import ValidationError as PydanticValidationError

from .errors import ArchtoolValidationError, Diagnostic
from .models import BuildingFile, OutlinePoint
from .resolved import (
    FLOOR_COLORS,
    Point,
    ResolvedBuilding,
    ResolvedModel,
    ResolvedOpening,
    ResolvedRoom,
    ResolvedWall,
)


def load_yaml(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ArchtoolValidationError([Diagnostic("error", str(path), f"could not read file: {exc}")]) from exc

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ArchtoolValidationError([Diagnostic("error", str(path), f"invalid YAML: {exc}")]) from exc

    if not isinstance(data, dict):
        raise ArchtoolValidationError(
            [Diagnostic("error", str(path), "file does not contain a YAML mapping at the top level")]
        )
    return data


def parse_schema(data: dict) -> BuildingFile:
    try:
        return BuildingFile.model_validate(data)
    except PydanticValidationError as exc:
        diagnostics = [
            Diagnostic("error", ".".join(str(p) for p in err["loc"]) or "<root>", err["msg"])
            for err in exc.errors()
        ]
        raise ArchtoolValidationError(diagnostics) from exc


def _suggest(name: str, candidates: list[str]) -> str:
    matches = difflib.get_close_matches(name, candidates, n=1)
    return f" (did you mean '{matches[0]}'?)" if matches else ""


def _alpha_seq():
    """Yield A, B, ..., Z, AA, AB, ..., for auto y-axis labels."""
    for length in itertools.count(1):
        for combo in itertools.product(string.ascii_uppercase, repeat=length):
            yield "".join(combo)


class _Resolver:
    """Resolves point names to coordinates, collecting diagnostics as it goes.

    Resolution does not stop at the first missing name: every element is
    attempted so that `archtool validate` can report all problems at once.
    """

    def __init__(self, bf: BuildingFile) -> None:
        self.bf = bf
        self.diagnostics: list[Diagnostic] = []
        # Axis labels are computed once, before points, so both the merged
        # points dict (auto point ids) and the SVG gridlines (_extract_axes)
        # agree on the same label for a given coordinate value.
        self._x_labels, self._y_labels = self._auto_label_axes()
        # Build the merged points dict once: outline inline defs + explicit points:.
        self.points = self._build_points_dict()

    def _auto_label_axes(self) -> tuple[dict[float, str], dict[float, str]]:
        """Assign a grid label to every distinct x and y value on the outline.

        Explicit `x_axis` / `y_axis` overrides on outline points are kept as
        given (conflicting values for the same label is an error). Every
        remaining, unlabeled coordinate value is auto-assigned the next
        unused label from the "1,2,3,..." / "A,B,C,...,Z,AA,..." sequences.
        """
        x_values: dict[float, str | None] = {}
        y_values: dict[float, str | None] = {}
        for op in self.bf.outline:
            x_values.setdefault(op.x, None)
            y_values.setdefault(op.y, None)
            if op.x_axis is not None:
                existing = x_values[op.x]
                if existing is not None and existing != op.x_axis:
                    self.diagnostics.append(
                        Diagnostic(
                            "error",
                            f"Outline point '{op.id or (op.x, op.y)}'",
                            f"x_axis '{op.x_axis}' conflicts with '{existing}' already assigned to x={op.x}",
                        )
                    )
                else:
                    x_values[op.x] = op.x_axis
            if op.y_axis is not None:
                existing = y_values[op.y]
                if existing is not None and existing != op.y_axis:
                    self.diagnostics.append(
                        Diagnostic(
                            "error",
                            f"Outline point '{op.id or (op.x, op.y)}'",
                            f"y_axis '{op.y_axis}' conflicts with '{existing}' already assigned to y={op.y}",
                        )
                    )
                else:
                    y_values[op.y] = op.y_axis

        used_x_labels = {label for label in x_values.values() if label is not None}
        used_y_labels = {label for label in y_values.values() if label is not None}

        numbers = (str(n) for n in itertools.count(1) if str(n) not in used_x_labels)
        for x in sorted(x_values):
            if x_values[x] is None:
                x_values[x] = next(numbers)

        letters = (letter for letter in _alpha_seq() if letter not in used_y_labels)
        for y in sorted(y_values):
            if y_values[y] is None:
                y_values[y] = next(letters)

        return (
            {x: label for x, label in x_values.items() if label is not None},
            {y: label for y, label in y_values.items() if label is not None},
        )

    def _outline_point_id(self, op: OutlinePoint) -> str:
        """The point id for an outline entry: explicit `id`, or derived from
        its (auto- or manually-labeled) x/y axis labels: `o<x_label><y_label>`.
        """
        return op.id if op.id is not None else f"o{self._x_labels[op.x]}{self._y_labels[op.y]}"

    def _build_points_dict(self) -> dict[str, Point]:
        """Merge inline outline point definitions with the explicit points: dict.

        Outline points take precedence; a name appearing in both locations is
        an error (the point is already defined by the outline entry).
        """
        points: dict[str, Point] = {}
        for op in self.bf.outline:
            point_id = self._outline_point_id(op)
            if point_id in points:
                self.diagnostics.append(
                    Diagnostic("error", f"Outline point '{point_id}'", "duplicate point id in outline")
                )
            else:
                points[point_id] = (op.x, op.y)
        for name, coord in self.bf.points.items():
            if name in points:
                self.diagnostics.append(
                    Diagnostic(
                        "error",
                        f"Point '{name}'",
                        "already defined as an outline point; remove it from points: to avoid the conflict",
                    )
                )
            else:
                points[name] = coord
        return points

    def _point(self, name: str, element: str) -> Point | None:
        if name not in self.points:
            self.diagnostics.append(
                Diagnostic(
                    "error",
                    element,
                    f"point '{name}' not found in points{_suggest(name, list(self.points.keys()))}",
                )
            )
            return None
        return self.points[name]

    def _points(self, names: list[str], element: str) -> list[Point] | None:
        coords: list[Point] = []
        ok = True
        for name in names:
            p = self._point(name, element)
            if p is None:
                ok = False
            else:
                coords.append(p)
        return coords if ok else None

    def _extract_axes(self) -> tuple[tuple[tuple[str, float], ...], tuple[tuple[str, float], ...]]:
        """Return the (label, value) pairs for every x/y axis, for SVG gridlines.

        Labels were already computed (and validated) by `_auto_label_axes`
        in `__init__`; this just reformats them sorted by coordinate value
        so gridlines render in spatial left-to-right / top-to-bottom order.
        """
        return (
            tuple(sorted(((label, x) for x, label in self._x_labels.items()), key=lambda t: t[1])),
            tuple(sorted(((label, y) for y, label in self._y_labels.items()), key=lambda t: t[1])),
        )

    def resolve(self) -> ResolvedModel | None:
        b = self.bf.building
        building = ResolvedBuilding(
            name=b.name,
            building_id=b.building_id,
            parcel_id=b.parcel_id,
            address=b.address,
            ceiling_height=b.ceiling_height,
            exterior_wall_thickness=b.exterior_wall_thickness,
            partition_wall_thickness=b.partition_wall_thickness,
            format_version=b.format_version,
        )

        # Outline coordinates come directly from the inline definitions.
        outline_coords = tuple((op.x, op.y) for op in self.bf.outline)

        exterior_walls = self._resolve_exterior_walls()
        walls = self._resolve_walls()
        openings = self._resolve_openings()
        rooms = self._resolve_rooms()
        x_axes, y_axes = self._extract_axes()

        if len(outline_coords) < 3:
            self.diagnostics.append(
                Diagnostic("error", "Building outline", "outline must have at least 3 points")
            )
            return None

        return ResolvedModel(
            building=building,
            outline=outline_coords,
            exterior_walls=tuple(exterior_walls),
            walls=tuple(walls),
            openings=tuple(openings),
            rooms=tuple(rooms),
            x_axes=x_axes,
            y_axes=y_axes,
        )

    def _resolve_exterior_walls(self) -> list[ResolvedWall]:
        ops = self.bf.outline
        n = len(ops)
        thickness = self.bf.building.exterior_wall_thickness
        ids = [self._outline_point_id(op) for op in ops]
        return [
            ResolvedWall(
                id=f"EXT_{ids[i]}_{ids[(i + 1) % n]}",
                p_from=(ops[i].x, ops[i].y),
                p_to=(ops[(i + 1) % n].x, ops[(i + 1) % n].y),
                thickness=thickness,
                type="load_bearing",
            )
            for i in range(n)
        ]

    def _resolve_walls(self) -> list[ResolvedWall]:
        b = self.bf.building
        walls = []
        for w in self.bf.walls:
            p_from = self._point(w.from_, f"Wall '{w.id}'")
            p_to = self._point(w.to, f"Wall '{w.id}'")
            thickness = w.thickness if w.thickness is not None else (
                b.exterior_wall_thickness if w.type == "load_bearing" else b.partition_wall_thickness
            )
            if p_from is not None and p_to is not None:
                walls.append(
                    ResolvedWall(
                        id=w.id, p_from=p_from, p_to=p_to,
                        thickness=thickness, type=w.type, justify=w.justify,
                    )
                )
        return walls

    def _resolve_openings(self) -> list[ResolvedOpening]:
        openings = []
        for o in self.bf.openings:
            p_from = self._point(o.from_, f"Opening '{o.id}'")
            p_to = self._point(o.to, f"Opening '{o.id}'")
            if p_from is not None and p_to is not None:
                openings.append(
                    ResolvedOpening(
                        id=o.id, type=o.type, p_from=p_from, p_to=p_to,
                        sill=o.sill, height=o.height, justify=o.justify,
                    )
                )
        return openings

    def _resolve_rooms(self) -> list[ResolvedRoom]:
        rooms = []
        for r in self.bf.rooms:
            coords = self._points(r.outline, f"Room '{r.id}'")
            if coords is not None:
                rooms.append(
                    ResolvedRoom(
                        id=r.id,
                        name=r.name,
                        floor=r.floor,
                        floor_color=FLOOR_COLORS[r.floor],
                        outline=tuple(coords),
                    )
                )
        return rooms


def resolve(bf: BuildingFile) -> tuple[ResolvedModel | None, list[Diagnostic]]:
    resolver = _Resolver(bf)
    model = resolver.resolve()
    return model, resolver.diagnostics
