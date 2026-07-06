"""Pydantic schema for the raw `dom_dane.yaml` building format.

These models mirror the YAML structure exactly (point names are plain
strings, not yet resolved to coordinates). Resolution into the canonical
in-memory model happens in `archtool.resolver`, never here.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

WallType = Literal["load_bearing", "partition"]
WallJustify = Literal["left", "center", "right"]
OpeningType = Literal["door", "window", "garage_gate", "empty_space"]
FloorMaterial = Literal["wood", "tiles", "laminate", "concrete", "carpet"]


class StrictModel(BaseModel):
    """Base model that rejects unknown fields, so typos surface as errors."""

    model_config = ConfigDict(extra="forbid")


class Building(StrictModel):
    name: str
    # Official registry identifiers. Not every building has one (e.g. a
    # design drafted before permitting/registration), so these are optional
    # rather than assumed present for every building expressed in the format.
    building_id: str | None = None
    parcel_id: str | None = None
    address: str | None = None
    ceiling_height: float
    exterior_wall_thickness: float
    partition_wall_thickness: float
    unit: str
    format_version: str
    spec: str


class OutlinePoint(StrictModel):
    """A building-outline vertex defined inline with its coordinates.

    The outline section is the single place to define perimeter points —
    no separate `points:` entry is needed for them.  Non-perimeter
    junction points (interior T-junctions, opening endpoints, etc.) that
    do *not* lie on the outer perimeter are still defined in `points:`.

    Minimal form is a plain ``[x, y]`` pair; the resolver then auto-labels
    the x/y architectural grid axes (1,2,3,... and A,B,C,...) and derives
    this point's id from them (``o<x_label><y_label>``). ``id``, `x_axis`,
    and `y_axis` may still be set explicitly to override the automatic
    values — e.g. ``x_axis: "2"`` marks the vertical gridline at this
    x-value as grid line "2". The SVG backend draws dashed reference
    lines and bubble labels for every distinct axis.
    """

    id: str | None = None  # auto-derived from axis labels when omitted
    x: float
    y: float
    x_axis: str | None = None  # names the vertical gridline at this x value
    y_axis: str | None = None  # names the horizontal gridline at this y value

    @model_validator(mode="before")
    @classmethod
    def _coerce_shorthand(cls, value: object) -> object:
        """Accept the minimal ``[x, y]`` list form in addition to a mapping."""
        if isinstance(value, (list, tuple)) and len(value) == 2:
            return {"x": value[0], "y": value[1]}
        return value


class Wall(StrictModel):
    id: str
    from_: str = Field(alias="from")
    to: str
    # thickness is optional; when omitted the resolver fills in the
    # building default: exterior_wall_thickness for load_bearing walls,
    # partition_wall_thickness for partition walls.
    thickness: float | None = None
    type: WallType
    justify: WallJustify = "center"


class Opening(StrictModel):
    id: str
    type: OpeningType
    from_: str = Field(alias="from")
    to: str
    sill: float
    height: float
    justify: WallJustify | None = None


class Room(StrictModel):
    id: str
    name: str
    floor: FloorMaterial
    outline: list[str]


class BuildingFile(StrictModel):
    """Top-level schema for a `dom_dane.yaml` file."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    building: Building
    # Outline is now a list of inline point definitions (OutlinePoint),
    # NOT a list of point names.  Each entry defines both the coordinate
    # and an optional architectural grid label for that position.
    outline: list[OutlinePoint]
    # Additional named points that do NOT appear on the building outline
    # (interior T-junction points, opening endpoints, etc.).  Optional —
    # omit entirely when all referenced points are already in `outline:`.
    points: dict[str, tuple[float, float]] = Field(default_factory=dict)
    walls: list[Wall] = Field(default_factory=list)
    openings: list[Opening] = Field(default_factory=list)
    rooms: list[Room] = Field(default_factory=list)
