"""Stage: geometry validation (SPEC.md section 10).

Operates only on the resolved model (coordinates), never on raw point
names — name resolution already happened in `archtool.resolver` (SPEC
rule 1). Rules 2-6 live here.
"""

from __future__ import annotations

from shapely.geometry import Polygon
from shapely.validation import explain_validity

from ..errors import Diagnostic
from ..geometry_utils import EPS, find_wall_for_opening
from ..resolved import Point, ResolvedModel


def _polygon_or_none(coords: tuple[Point, ...], element: str, diagnostics: list[Diagnostic]) -> Polygon | None:
    if len(coords) < 3:
        diagnostics.append(
            Diagnostic("error", element, f"polygon has only {len(coords)} point(s); at least 3 are required")
        )
        return None
    poly = Polygon(coords)
    if not poly.is_valid:
        diagnostics.append(Diagnostic("error", element, f"is not a valid polygon ({explain_validity(poly)})"))
        return None
    return poly


def validate_geometry(model: ResolvedModel) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    outline_poly = _polygon_or_none(model.outline, "Building outline", diagnostics)

    room_polys: dict[str, Polygon] = {}
    for room in model.rooms:
        poly = _polygon_or_none(room.outline, f"Room '{room.id}'", diagnostics)
        if poly is not None:
            room_polys[room.id] = poly

    all_walls = model.all_walls()
    for opening in model.openings:
        if find_wall_for_opening(opening, all_walls) is None:
            diagnostics.append(
                Diagnostic(
                    "error",
                    f"Opening '{opening.id}'",
                    "does not lie on the axis of any wall within its span",
                )
            )
        total = opening.sill + opening.height
        if total > model.building.ceiling_height + EPS:
            diagnostics.append(
                Diagnostic(
                    "error",
                    f"Opening '{opening.id}'",
                    f"sill + height ({total:.1f} cm) exceeds ceiling height "
                    f"({model.building.ceiling_height:.1f} cm)",
                )
            )

    if outline_poly is not None:
        for room in model.rooms:
            poly = room_polys.get(room.id)
            if poly is not None and not outline_poly.covers(poly):
                diagnostics.append(Diagnostic("error", f"Room '{room.id}'", "lies outside the building outline"))

        total_room_area = sum(p.area for p in room_polys.values())
        if total_room_area >= outline_poly.area:
            diagnostics.append(
                Diagnostic(
                    "error",
                    "Rooms",
                    f"total room area ({total_room_area / 10000:.2f} m²) is not less than the "
                    f"building outline area ({outline_poly.area / 10000:.2f} m²)",
                )
            )

    return diagnostics
