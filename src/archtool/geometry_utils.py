"""Geometry helpers shared between the validator and backends.

Kept separate from `archtool.validation` because backends (the SVG
renderer) need the same "which wall does this opening sit on" logic to
know how thick a gap to cut — that is not itself a validation concern.
"""

from __future__ import annotations

from shapely.geometry import LineString
from shapely.geometry import Point as ShapelyPoint

from .resolved import Point, ResolvedOpening, ResolvedWall

# Floating point tolerance for "on the axis" / "within the span" checks, in cm.
EPS = 1e-6


def _point_on_wall_axis(wall: ResolvedWall, point: Point) -> bool:
    axis = LineString([wall.p_from, wall.p_to])
    length = axis.length
    if length < EPS:
        return False
    pt = ShapelyPoint(point)
    if axis.distance(pt) > EPS:
        return False
    t = axis.project(pt)
    return -EPS <= t <= length + EPS


def find_wall_for_opening(
    opening: ResolvedOpening, walls: tuple[ResolvedWall, ...] | list[ResolvedWall]
) -> ResolvedWall | None:
    """Return the wall whose axis contains the opening, within its span."""
    for wall in walls:
        if _point_on_wall_axis(wall, opening.p_from) and _point_on_wall_axis(wall, opening.p_to):
            return wall
    return None
