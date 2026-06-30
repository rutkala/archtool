"""Pydantic schema for the raw `dom_dane.yaml` building format.

These models mirror the YAML structure exactly (point names are plain
strings, not yet resolved to coordinates). Resolution into the canonical
in-memory model happens in `archtool.resolver`, never here.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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


class Wall(StrictModel):
    id: str
    from_: str = Field(alias="from")
    to: str
    thickness: float
    type: WallType
    justify: WallJustify = "center"


class Opening(StrictModel):
    id: str
    type: OpeningType
    from_: str = Field(alias="from")
    to: str
    sill: float
    height: float


class Room(StrictModel):
    id: str
    name: str
    floor: FloorMaterial
    outline: list[str]


class BuildingFile(StrictModel):
    """Top-level schema for a `dom_dane.yaml` file."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    building: Building
    points: dict[str, tuple[float, float]]
    outline: list[str]
    walls: list[Wall] = Field(default_factory=list)
    openings: list[Opening] = Field(default_factory=list)
    rooms: list[Room] = Field(default_factory=list)
