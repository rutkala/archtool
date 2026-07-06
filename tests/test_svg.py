from __future__ import annotations

import math
import xml.etree.ElementTree as ET

import pytest
from shapely.geometry import Point as ShapelyPoint
from shapely.geometry import Polygon
from shapely.ops import unary_union

from archtool.backends.svg import (
    GARAGE_GATE_COLOR,
    WINDOW_LINE_COLOR,
    _extend_dangling_ends,
    _offset_range,
    _render_opening,
    _wall_corners_at_point,
    _wall_joints,
    _wall_rectangle,
    render_svg,
    write_svg,
)
from archtool.pipeline import load_and_validate
from archtool.resolved import Point, ResolvedOpening, ResolvedWall


def test_render_svg_is_well_formed_xml(fixture_path) -> None:
    model, _ = load_and_validate(fixture_path)
    svg_text = render_svg(model)

    root = ET.fromstring(svg_text)
    assert root.tag.endswith("svg")


def test_render_svg_contains_room_names_and_colors(fixture_path) -> None:
    model, _ = load_and_validate(fixture_path)
    svg_text = render_svg(model)

    for room in model.rooms:
        assert room.name in svg_text
        assert room.floor_color in svg_text


def test_render_svg_is_deterministic(fixture_path) -> None:
    model, _ = load_and_validate(fixture_path)
    assert render_svg(model) == render_svg(model)


def test_write_svg_writes_file(fixture_path, tmp_path) -> None:
    model, _ = load_and_validate(fixture_path)
    out_path = tmp_path / "out.svg"

    result = write_svg(model, out_path)

    assert result == out_path
    assert out_path.exists()
    assert out_path.read_text(encoding="utf-8") == render_svg(model)


def test_wall_joint_patch_closes_corner_gap() -> None:
    # Each wall is drawn as an independent rectangle with flat (butt) ends.
    # At a corner where two such rectangles meet, one quadrant of the
    # corner is covered by neither rectangle (visible as a stair-step
    # notch). _wall_joints patches that gap with the junction's bounding
    # box; this proves both that the gap exists and that the patch closes
    # it.
    wall_a = ResolvedWall(id="A", p_from=(-100.0, 0.0), p_to=(0.0, 0.0), thickness=20.0, type="load_bearing")
    wall_b = ResolvedWall(id="B", p_from=(0.0, 0.0), p_to=(0.0, 100.0), thickness=20.0, type="load_bearing")
    walls = (wall_a, wall_b)

    rects = [Polygon(_wall_rectangle(w.p_from, w.p_to, w.thickness)) for w in walls]
    union_without_patch = unary_union(rects)

    gap_point = ShapelyPoint(5.0, -5.0)  # the unfilled "outer corner" quadrant
    assert not union_without_patch.covers(gap_point)

    joints = _wall_joints(walls)
    assert joints == [(-10.0, -10.0, 10.0, 10.0)]

    x0, y0, x1, y1 = joints[0]
    patch = Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    union_with_patch = unary_union([*rects, patch])

    assert union_with_patch.covers(gap_point)


def test_wall_joints_ignored_for_unshared_endpoints() -> None:
    wall = ResolvedWall(id="A", p_from=(0.0, 0.0), p_to=(100.0, 0.0), thickness=20.0, type="partition")
    assert _wall_joints((wall,)) == []


def test_dangling_end_is_extended_by_half_thickness() -> None:
    # A wall end that touches nothing else still has a flat butt cap sitting
    # exactly on the axis point, i.e. it visually stops mid-thickness. The
    # open end should extend by thickness/2 along the wall's own axis, the
    # same effect as SVG stroke-linecap="square", so a full, flush face is
    # drawn instead of half a wall stopping at a bare point.
    wall = ResolvedWall(id="A", p_from=(0.0, 0.0), p_to=(100.0, 0.0), thickness=20.0, type="partition")

    p_from, p_to = _extend_dangling_ends((wall,))["A"]

    assert p_from == (-10.0, 0.0)
    assert p_to == (110.0, 0.0)


def test_connected_end_is_not_extended() -> None:
    # A's "to" touches B's "from" - that end is a real junction (handled by
    # _wall_joints), not a dangling end, so it must not be stretched.
    wall_a = ResolvedWall(id="A", p_from=(0.0, 0.0), p_to=(100.0, 0.0), thickness=20.0, type="load_bearing")
    wall_b = ResolvedWall(id="B", p_from=(100.0, 0.0), p_to=(100.0, 100.0), thickness=20.0, type="load_bearing")

    ends = _extend_dangling_ends((wall_a, wall_b))

    assert ends["A"] == ((-10.0, 0.0), (100.0, 0.0))  # "from" dangling, "to" connected
    assert ends["B"] == ((100.0, 0.0), (100.0, 110.0))  # "from" connected, "to" dangling


def test_dangling_end_extension_closes_open_end_gap() -> None:
    # s_6b in examples/czest_gruszowa_60/dom_dane.yaml is exactly this case:
    # an interior wall whose far end touches no other wall.
    wall = ResolvedWall(id="A", p_from=(0.0, 0.0), p_to=(100.0, 0.0), thickness=20.0, type="partition")

    bare_rect = Polygon(_wall_rectangle(wall.p_from, wall.p_to, wall.thickness))
    end_point = ShapelyPoint(100.0, 0.0)
    assert not bare_rect.buffer(0).covers(end_point.buffer(10.0 - 0.01))  # half the wall's material is missing

    p_from, p_to = _extend_dangling_ends((wall,))["A"]
    extended_rect = Polygon(_wall_rectangle(p_from, p_to, wall.thickness))
    assert extended_rect.covers(end_point.buffer(10.0 - 0.01))


def test_justify_right_puts_full_thickness_on_right_face() -> None:
    # Walking from p_from to p_to (here due east), "right" puts all the
    # material on the right-hand side - i.e. toward +y in this y-down
    # system - so the axis itself becomes the wall's *left* (north) face.
    o_min, o_max = _offset_range(thickness=20.0, justify="right")
    assert (o_min, o_max) == (0.0, 20.0)

    rect = Polygon(_wall_rectangle((0.0, 0.0), (100.0, 0.0), thickness=20.0, justify="right"))
    minx, miny, maxx, maxy = rect.bounds
    assert (miny, maxy) == (0.0, 20.0)


def test_justify_left_puts_full_thickness_on_left_face() -> None:
    o_min, o_max = _offset_range(thickness=20.0, justify="left")
    assert (o_min, o_max) == (-20.0, 0.0)

    rect = Polygon(_wall_rectangle((0.0, 0.0), (100.0, 0.0), thickness=20.0, justify="left"))
    minx, miny, maxx, maxy = rect.bounds
    assert (miny, maxy) == (-20.0, 0.0)


def test_wall_joint_patch_for_mismatched_justify_does_not_overreach() -> None:
    # The d_pgv/d_pgh corner in examples/czest_gruszowa_60/dom_dane.yaml,
    # reduced to its essentials: a "left"-justified 15cm wall arriving from
    # the north, meeting a center-justified 15cm wall departing east, at
    # (0,0). Only x<0 (the open room on the wall's unbuilt side) should be
    # left uncovered - the patch must not bleed into it just because the
    # old fixed-size-square approach used to.
    # A's direction is (0,1); justify="left" puts material toward +x (since
    # the right-hand perpendicular of (0,1) is (-1,0), i.e. "left" = +x).
    wall_a = ResolvedWall(
        id="A", p_from=(0.0, -100.0), p_to=(0.0, 0.0), thickness=15.0, type="partition", justify="left"
    )
    wall_b = ResolvedWall(id="B", p_from=(0.0, 0.0), p_to=(100.0, 0.0), thickness=15.0, type="partition")

    joints = _wall_joints((wall_a, wall_b))
    assert joints == [(0.0, -7.5, 15.0, 7.5)]  # x stays within [0, 15], never goes negative


def test_gruszowa_d_pgv_is_flush_with_exterior_wall(gruszowa_fixture_path) -> None:
    # d_pgv (15cm, justify="left") continues the 30cm exterior wall below
    # o2C=(240,200), sharing that exact point rather than a duplicated one.
    # Centering both on the same axis would leave their faces 7.5cm apart
    # on both sides; "left" justification keeps d_pgv's utility-room-facing
    # face flush with the exterior wall's face, without moving any points.
    model, _ = load_and_validate(gruszowa_fixture_path)

    exterior = next(w for w in model.exterior_walls if w.id == "EXT_o2C_o2A")
    d_pgv = next(w for w in model.walls if w.id == "d_pgv")

    assert d_pgv.p_from == exterior.p_from == (240.0, 200.0)  # same point, not a duplicate
    assert d_pgv.justify == "left"

    exterior_rect = Polygon(_wall_rectangle(exterior.p_from, exterior.p_to, exterior.thickness))
    d_pgv_rect = Polygon(_wall_rectangle(d_pgv.p_from, d_pgv.p_to, d_pgv.thickness, d_pgv.justify))

    exterior_right_face = exterior_rect.bounds[2]  # max x
    d_pgv_right_face = d_pgv_rect.bounds[2]

    assert exterior_right_face == pytest.approx(255.0)
    assert d_pgv_right_face == pytest.approx(exterior_right_face)


def test_render_svg_includes_joint_patches_for_fixture(fixture_path) -> None:
    model, _ = load_and_validate(fixture_path)
    svg_text = render_svg(model)

    joints = _wall_joints(model.all_walls())
    assert joints, "expected at least one wall junction in the fixture"
    for x0, y0, x1, y1 in joints:
        assert f'x="{x0:.2f}" y="{y0:.2f}" width="{x1 - x0:.2f}" height="{y1 - y0:.2f}"' in svg_text


def _dangling_cap_far_corners(wall: ResolvedWall, point: Point) -> list[Point]:
    """The two far corners of the square cap a dangling end should grow
    into once extended (justify-aware: an off-center wall's cap isn't
    symmetric around the axis point, only its own actual face corners,
    pushed `thickness/2` further along the wall's axis, away from it).
    """
    (x1, y1), (x2, y2) = wall.p_from, wall.p_to
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length == 0:
        return []
    ux, uy = dx / length, dy / length
    away = (-ux, -uy) if point == wall.p_from else (ux, uy)
    h = wall.thickness / 2
    far = (point[0] + away[0] * h, point[1] + away[1] * h)
    return _wall_corners_at_point(wall, far)


def test_all_dangling_ends_covered_for_all_example_fixtures(all_example_paths) -> None:
    # For a truly unconnected end (touched by only one wall), the cap's far
    # corners - the wall's own (justify-aware) face corners, pushed
    # thickness/2 further along its axis - are exactly what the extension
    # in _extend_dangling_ends should fill. A symmetric disk around the
    # bare axis point is the wrong shape once a wall can be off-center.
    for path in all_example_paths:
        model, _ = load_and_validate(path)
        all_walls = model.all_walls()
        wall_ends = _extend_dangling_ends(all_walls)
        rects = [Polygon(_wall_rectangle(*wall_ends[w.id], w.thickness, w.justify)) for w in all_walls]
        patches = [Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]) for x0, y0, x1, y1 in _wall_joints(all_walls)]
        union = unary_union(rects + patches).buffer(0.01)  # the cap's far edge sits exactly on the union boundary

        counts: dict[tuple[float, float], int] = {}
        for w in all_walls:
            counts[w.p_from] = counts.get(w.p_from, 0) + 1
            counts[w.p_to] = counts.get(w.p_to, 0) + 1

        for wall in all_walls:
            for point in (wall.p_from, wall.p_to):
                if counts[point] >= 2:
                    continue  # a real junction, covered by the corner-based test below
                for corner in _dangling_cap_far_corners(wall, point):
                    assert union.covers(ShapelyPoint(corner)), (
                        f"{path.name}: {wall.id} dangling end {point} cap corner {corner} is not covered"
                    )


def test_garage_gate_renders_distinct_symbol() -> None:
    wall = ResolvedWall(id="W", p_from=(0.0, 0.0), p_to=(300.0, 0.0), thickness=30.0, type="load_bearing")
    opening = ResolvedOpening(id="G", type="garage_gate", p_from=(50.0, 0.0), p_to=(250.0, 0.0), sill=0.0, height=220.0)

    rendered = _render_opening(opening, (wall,), default_thickness=15.0)

    assert GARAGE_GATE_COLOR in rendered
    assert WINDOW_LINE_COLOR not in rendered
    assert "<path" not in rendered  # no swing arc - garage doors don't hinge open


def test_empty_space_has_no_symbol_only_the_gap() -> None:
    wall = ResolvedWall(id="W", p_from=(0.0, 0.0), p_to=(300.0, 0.0), thickness=30.0, type="load_bearing")
    opening = ResolvedOpening(id="E", type="empty_space", p_from=(50.0, 0.0), p_to=(250.0, 0.0), sill=0.0, height=200.0)

    rendered = _render_opening(opening, (wall,), default_thickness=15.0)

    assert rendered.count("<") == 1  # only the one cut <polygon>, nothing drawn across it
    assert "<polygon" in rendered


def test_gruszowa_fixture_demonstrates_all_four_opening_types(gruszowa_fixture_path) -> None:
    model, _ = load_and_validate(gruszowa_fixture_path)
    types_present = {opening.type for opening in model.openings}
    assert types_present == {"door", "window", "garage_gate", "empty_space"}


def test_all_wall_junction_corners_covered_for_all_example_fixtures(all_example_paths) -> None:
    # At a junction, checking a symmetric disk around the bare axis point
    # is unsound once walls can be off-center ("justify"): the axis point
    # may legitimately have open room on one side. What must hold instead
    # is that every wall's own face-corners at that point - the actual
    # extent of its material - end up covered by the combined wall fill.
    for path in all_example_paths:
        model, _ = load_and_validate(path)
        all_walls = model.all_walls()
        wall_ends = _extend_dangling_ends(all_walls)
        rects = [Polygon(_wall_rectangle(*wall_ends[w.id], w.thickness, w.justify)) for w in all_walls]
        patches = [Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]) for x0, y0, x1, y1 in _wall_joints(all_walls)]
        union = unary_union(rects + patches)

        points_to_walls: dict[tuple[float, float], list[ResolvedWall]] = {}
        for w in all_walls:
            points_to_walls.setdefault(w.p_from, []).append(w)
            points_to_walls.setdefault(w.p_to, []).append(w)

        # Grow the union by a hair rather than the test points: each corner
        # sits exactly on a wall's own outer boundary by construction, so a
        # disk *around* the corner would always be ~half "outside" (that's
        # what a boundary is) - that's not a gap, just floating-point fuzz
        # at the edge we're asserting is covered.
        union_padded = union.buffer(0.01)

        for point, walls_at_point in points_to_walls.items():
            if len(walls_at_point) < 2:
                continue
            for wall in walls_at_point:
                for corner in _wall_corners_at_point(wall, point):
                    assert union_padded.covers(ShapelyPoint(corner)), (
                        f"{path.name}: {wall.id} corner {corner} at junction {point} is not covered"
                    )
