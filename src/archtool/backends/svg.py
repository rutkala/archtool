"""SVG backend: renders a 2D floor plan from the resolved model.

SPEC.md's coordinate system (x right, y down) already matches SVG's, so
no axis flip is needed here (unlike Y-up export targets — see SPEC.md
section 1.1).
"""

from __future__ import annotations

import math
from pathlib import Path
from xml.sax.saxutils import escape

from shapely.geometry import Polygon

from ..geometry_utils import find_wall_for_opening
from ..resolved import Point, ResolvedModel, ResolvedOpening, ResolvedWall

MARGIN_CM = 100.0
WALL_COLOR = "#3a3a3a"
OPENING_GAP_COLOR = "#ffffff"
WINDOW_LINE_COLOR = "#3a8fd6"
ROOM_STROKE_COLOR = "#1a1a1a"
ROOM_LABEL_COLOR = "#1a1a1a"
OUTLINE_STROKE_COLOR = "#000000"


def _offset_range(thickness: float, justify: str) -> tuple[float, float]:
    """Perpendicular offset range (min, max) from the axis for a wall's
    cross-section, per SPEC.md section 4.

    The perpendicular vector used throughout this module, (-uy, ux), is the
    right-hand side when walking from p_from to p_to. "right" therefore
    spans [0, thickness] (material on the right of the axis); "left" spans
    [-thickness, 0]; "center" splits evenly, [-thickness/2, thickness/2].
    """
    if justify == "right":
        return (0.0, thickness)
    if justify == "left":
        return (-thickness, 0.0)
    return (-thickness / 2, thickness / 2)


def _wall_rectangle(p_from: Point, p_to: Point, thickness: float, justify: str = "center") -> list[Point]:
    (x1, y1), (x2, y2) = p_from, p_to
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length == 0:
        return []
    ux, uy = dx / length, dy / length
    px, py = -uy, ux  # perpendicular unit vector (right-hand side of travel)
    o_min, o_max = _offset_range(thickness, justify)
    return [
        (x1 + px * o_max, y1 + py * o_max),
        (x2 + px * o_max, y2 + py * o_max),
        (x2 + px * o_min, y2 + py * o_min),
        (x1 + px * o_min, y1 + py * o_min),
    ]


def _points_attr(coords) -> str:
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in coords)


def _wall_thicknesses_by_point(walls: tuple[ResolvedWall, ...]) -> dict[Point, list[float]]:
    thicknesses_by_point: dict[Point, list[float]] = {}
    for wall in walls:
        for point in (wall.p_from, wall.p_to):
            thicknesses_by_point.setdefault(point, []).append(wall.thickness)
    return thicknesses_by_point


def _wall_corners_at_point(wall: ResolvedWall, point: Point) -> list[Point]:
    """The two points where wall's cross-section edges pass through `point`."""
    (x1, y1), (x2, y2) = wall.p_from, wall.p_to
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length == 0:
        return [point]
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    o_min, o_max = _offset_range(wall.thickness, wall.justify)
    return [(point[0] + px * o_min, point[1] + py * o_min), (point[0] + px * o_max, point[1] + py * o_max)]


def _wall_joints(walls: tuple[ResolvedWall, ...]) -> list[tuple[float, float, float, float]]:
    """Bounding box (min_x, min_y, max_x, max_y) of every point where 2+
    wall rectangles meet.

    Each wall is drawn as an independent rectangle with flat (butt) ends, so
    at any corner or T/L junction a small area of the corner is left
    unfilled (visible as a stair-step notch). Patching the junction's own
    footprint over each shared endpoint closes that gap — the same fix the
    original dom_viewer.html applied via its `_wezly` (node) markers, here
    generalised to off-center (`justify`) walls: the patch is sized to the
    actual corners each wall contributes at that point, not just a square
    of the thickest wall's width, since an off-center wall's footprint
    isn't necessarily centered on the shared point.
    """
    points_to_walls: dict[Point, list[ResolvedWall]] = {}
    for wall in walls:
        points_to_walls.setdefault(wall.p_from, []).append(wall)
        points_to_walls.setdefault(wall.p_to, []).append(wall)

    patches = []
    for point, walls_at_point in sorted(points_to_walls.items()):
        if len(walls_at_point) < 2:
            continue
        xs = [point[0]]
        ys = [point[1]]
        for wall in walls_at_point:
            for cx, cy in _wall_corners_at_point(wall, point):
                xs.append(cx)
                ys.append(cy)
        patches.append((min(xs), min(ys), max(xs), max(ys)))
    return patches


def _extend_dangling_ends(walls: tuple[ResolvedWall, ...]) -> dict[str, tuple[Point, Point]]:
    """Stretch each wall's unconnected (dangling) endpoints by half its own
    thickness, along its own axis.

    A wall end that touches no other wall still has a flat butt cap sitting
    exactly on the axis point — i.e. only half the wall's material is
    drawn there, as if it stopped mid-brick. Extending by thickness/2 (the
    same effect as SVG's `stroke-linecap="square"`) shows a finished,
    flush face instead. Ends that connect to another wall are left alone;
    `_wall_joints` already patches those corners.
    """
    counts = {point: len(thicknesses) for point, thicknesses in _wall_thicknesses_by_point(walls).items()}

    extended: dict[str, tuple[Point, Point]] = {}
    for wall in walls:
        p_from, p_to = wall.p_from, wall.p_to
        dx, dy = p_to[0] - p_from[0], p_to[1] - p_from[1]
        length = math.hypot(dx, dy)
        if length == 0:
            extended[wall.id] = (p_from, p_to)
            continue
        ux, uy = dx / length, dy / length
        h = wall.thickness / 2
        if counts[p_from] < 2:
            p_from = (p_from[0] - ux * h, p_from[1] - uy * h)
        if counts[p_to] < 2:
            p_to = (p_to[0] + ux * h, p_to[1] + uy * h)
        extended[wall.id] = (p_from, p_to)
    return extended


def _window_lines(opening: ResolvedOpening, thickness: float, justify: str = "center") -> str:
    (x1, y1), (x2, y2) = opening.p_from, opening.p_to
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length == 0:
        return ""
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    o_min, o_max = _offset_range(thickness, justify)
    center = (o_min + o_max) / 2  # midpoint of the wall's actual cross-section, not the axis
    quarter = thickness / 4
    lines = []
    for offset in (center - quarter, center + quarter):
        ox, oy = px * offset, py * offset
        lines.append(
            f'<line x1="{x1 + ox:.2f}" y1="{y1 + oy:.2f}" x2="{x2 + ox:.2f}" y2="{y2 + oy:.2f}" '
            f'stroke="{WINDOW_LINE_COLOR}" stroke-width="2" />'
        )
    return "\n".join(lines)


def _door_swing(opening: ResolvedOpening) -> str:
    (x1, y1), (x2, y2) = opening.p_from, opening.p_to
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length == 0:
        return ""
    ux, uy = dx / length, dy / length
    px, py = -uy, ux  # swing into the same side as the wall rectangle's "+" face
    leaf_x, leaf_y = x1 + px * length, y1 + py * length
    return (
        f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{leaf_x:.2f}" y2="{leaf_y:.2f}" '
        f'stroke="{WALL_COLOR}" stroke-width="2" />\n'
        f'<path d="M {leaf_x:.2f} {leaf_y:.2f} A {length:.2f} {length:.2f} 0 0 0 {x2:.2f} {y2:.2f}" '
        f'fill="none" stroke="{WALL_COLOR}" stroke-width="1" stroke-dasharray="4 3" />'
    )


def _render_opening(opening: ResolvedOpening, walls: tuple[ResolvedWall, ...], default_thickness: float) -> str:
    wall = find_wall_for_opening(opening, walls)
    thickness = wall.thickness if wall is not None else default_thickness
    justify = wall.justify if wall is not None else "center"
    cut = _wall_rectangle(opening.p_from, opening.p_to, thickness, justify)
    if not cut:
        return ""
    parts = [f'<polygon points="{_points_attr(cut)}" fill="{OPENING_GAP_COLOR}" />']
    if opening.type == "door":
        parts.append(_door_swing(opening))
    else:
        parts.append(_window_lines(opening, thickness, justify))
    return "\n".join(parts)


def render_svg(model: ResolvedModel) -> str:
    xs = [x for x, _ in model.outline]
    ys = [y for _, y in model.outline]
    min_x, max_x = min(xs) - MARGIN_CM, max(xs) + MARGIN_CM
    min_y, max_y = min(ys) - MARGIN_CM, max(ys) + MARGIN_CM
    width, height = max_x - min_x, max_y - min_y

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{min_x:.2f} {min_y:.2f} {width:.2f} {height:.2f}" '
        f'font-family="sans-serif">',
        f'<rect x="{min_x:.2f}" y="{min_y:.2f}" width="{width:.2f}" height="{height:.2f}" fill="#ffffff" />',
        f'<polygon points="{_points_attr(model.outline)}" fill="none" '
        f'stroke="{OUTLINE_STROKE_COLOR}" stroke-width="1" />',
    ]

    for room in sorted(model.rooms, key=lambda r: r.id):
        parts.append(
            f'<polygon points="{_points_attr(room.outline)}" fill="{room.floor_color}" '
            f'stroke="{ROOM_STROKE_COLOR}" stroke-width="1" />'
        )

    all_walls = model.all_walls()
    wall_ends = _extend_dangling_ends(all_walls)
    for wall in sorted(all_walls, key=lambda w: w.id):
        p_from, p_to = wall_ends[wall.id]
        rect = _wall_rectangle(p_from, p_to, wall.thickness, wall.justify)
        if rect:
            parts.append(f'<polygon points="{_points_attr(rect)}" fill="{WALL_COLOR}" />')

    for min_x_p, min_y_p, max_x_p, max_y_p in _wall_joints(all_walls):
        parts.append(
            f'<rect x="{min_x_p:.2f}" y="{min_y_p:.2f}" width="{max_x_p - min_x_p:.2f}" '
            f'height="{max_y_p - min_y_p:.2f}" fill="{WALL_COLOR}" />'
        )

    for opening in sorted(model.openings, key=lambda o: o.id):
        rendered = _render_opening(opening, all_walls, model.building.partition_wall_thickness)
        if rendered:
            parts.append(rendered)

    for room in sorted(model.rooms, key=lambda r: r.id):
        poly = Polygon(room.outline)
        cx, cy = poly.centroid.x, poly.centroid.y
        area_m2 = poly.area / 10000
        parts.append(
            f'<text x="{cx:.2f}" y="{cy:.2f}" fill="{ROOM_LABEL_COLOR}" font-size="18" '
            f'text-anchor="middle">{escape(room.name)}</text>'
        )
        parts.append(
            f'<text x="{cx:.2f}" y="{cy + 22:.2f}" fill="{ROOM_LABEL_COLOR}" font-size="14" '
            f'text-anchor="middle">{area_m2:.1f} m²</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


def write_svg(model: ResolvedModel, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_svg(model), encoding="utf-8")
    return out_path
