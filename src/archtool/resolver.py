"""Stage 1: load YAML, validate schema, resolve named points into coordinates.

Produces the canonical `ResolvedModel` (see `archtool.resolved`). This is
the only module allowed to know about point *names* — everything
downstream works in plain coordinates.
"""

from __future__ import annotations

import difflib
from pathlib import Path

import yaml
from pydantic import ValidationError as PydanticValidationError

from .errors import ArchtoolValidationError, Diagnostic
from .models import BuildingFile
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


class _Resolver:
    """Resolves point names to coordinates, collecting diagnostics as it goes.

    Resolution does not stop at the first missing name: every element is
    attempted so that `archtool validate` can report all problems at once.
    """

    def __init__(self, bf: BuildingFile) -> None:
        self.bf = bf
        self.points = bf.points
        self.diagnostics: list[Diagnostic] = []

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

        outline_coords = self._points(self.bf.outline, "Building outline")
        exterior_walls = self._resolve_exterior_walls(outline_coords, building.exterior_wall_thickness)
        walls = self._resolve_walls()
        openings = self._resolve_openings()
        rooms = self._resolve_rooms()

        if outline_coords is None:
            return None

        return ResolvedModel(
            building=building,
            outline=tuple(outline_coords),
            exterior_walls=tuple(exterior_walls),
            walls=tuple(walls),
            openings=tuple(openings),
            rooms=tuple(rooms),
        )

    def _resolve_exterior_walls(self, outline_coords: list[Point] | None, thickness: float) -> list[ResolvedWall]:
        if outline_coords is None:
            return []
        names = self.bf.outline
        n = len(outline_coords)
        return [
            ResolvedWall(
                id=f"EXT_{names[i]}_{names[(i + 1) % n]}",
                p_from=outline_coords[i],
                p_to=outline_coords[(i + 1) % n],
                thickness=thickness,
                type="load_bearing",
            )
            for i in range(n)
        ]

    def _resolve_walls(self) -> list[ResolvedWall]:
        walls = []
        for w in self.bf.walls:
            p_from = self._point(w.from_, f"Wall '{w.id}'")
            p_to = self._point(w.to, f"Wall '{w.id}'")
            if p_from is not None and p_to is not None:
                walls.append(
                    ResolvedWall(
                        id=w.id, p_from=p_from, p_to=p_to, thickness=w.thickness, type=w.type, justify=w.justify
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
                    ResolvedOpening(id=o.id, type=o.type, p_from=p_from, p_to=p_to, sill=o.sill, height=o.height)
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
