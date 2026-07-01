"""The canonical resolved model.

This is the only structure backends are allowed to read (see CLAUDE.md:
"Every backend reads THIS, never the raw YAML"). All point names have
already been replaced by `(x, y)` coordinates in centimetres.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

Point = tuple[float, float]

# SPEC.md section 7: floor material -> colour mapping.
FLOOR_COLORS: dict[str, str] = {
    "wood": "#d9bd95",
    "tiles": "#d8d4cb",
    "laminate": "#c9a872",
    "concrete": "#9a9a93",
    "carpet": "#b7a8a0",
}


@dataclass(frozen=True)
class ResolvedWall:
    id: str
    p_from: Point
    p_to: Point
    thickness: float
    type: str  # "load_bearing" | "partition"
    justify: str = "center"  # "left" | "center" | "right", relative to p_from -> p_to


@dataclass(frozen=True)
class ResolvedOpening:
    id: str
    type: str  # "door" | "window" | "garage_gate" | "empty_space"
    p_from: Point
    p_to: Point
    sill: float
    height: float
    justify: str | None = None  # overrides the host wall's justify for the cut; None = inherit


@dataclass(frozen=True)
class ResolvedRoom:
    id: str
    name: str
    floor: str
    floor_color: str
    outline: tuple[Point, ...]


@dataclass(frozen=True)
class ResolvedBuilding:
    name: str
    building_id: str | None
    parcel_id: str | None
    address: str | None
    ceiling_height: float
    exterior_wall_thickness: float
    partition_wall_thickness: float
    format_version: str


@dataclass(frozen=True)
class ResolvedModel:
    """The canonical, JSON-serialisable building model. Backends read only this."""

    building: ResolvedBuilding
    outline: tuple[Point, ...]
    exterior_walls: tuple[ResolvedWall, ...]
    walls: tuple[ResolvedWall, ...]
    openings: tuple[ResolvedOpening, ...]
    rooms: tuple[ResolvedRoom, ...]
    # Architectural grid axes declared in the outline.
    # Each entry is (label, coordinate_value); sorted by coordinate value
    # so SVG rendering draws them in spatial order.
    x_axes: tuple[tuple[str, float], ...] = ()  # vertical gridlines: (label, x)
    y_axes: tuple[tuple[str, float], ...] = ()  # horizontal gridlines: (label, y)

    def to_dict(self) -> dict:
        return asdict(self)

    def all_walls(self) -> tuple[ResolvedWall, ...]:
        """Exterior and interior walls combined, exterior first."""
        return self.exterior_walls + self.walls
