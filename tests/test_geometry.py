from __future__ import annotations

import pytest

from archtool.errors import ArchtoolValidationError
from archtool.pipeline import load_and_validate
from archtool.resolved import (
    ResolvedBuilding,
    ResolvedModel,
    ResolvedOpening,
    ResolvedRoom,
    ResolvedWall,
)
from archtool.validation.geometry import validate_geometry

BUILDING = ResolvedBuilding(
    name="Test",
    building_id="B1",
    parcel_id="P1",
    address=None,
    ceiling_height=250.0,
    exterior_wall_thickness=30.0,
    partition_wall_thickness=15.0,
    format_version="1.0",
)

OUTLINE = ((0.0, 0.0), (1000.0, 0.0), (1000.0, 1000.0), (0.0, 1000.0))


def _exterior_walls() -> tuple[ResolvedWall, ...]:
    n = len(OUTLINE)
    return tuple(
        ResolvedWall(
            id=f"EXT_{i}",
            p_from=OUTLINE[i],
            p_to=OUTLINE[(i + 1) % n],
            thickness=BUILDING.exterior_wall_thickness,
            type="load_bearing",
        )
        for i in range(n)
    )


def _base_model(**overrides) -> ResolvedModel:
    fields = dict(
        building=BUILDING,
        outline=OUTLINE,
        exterior_walls=_exterior_walls(),
        walls=(),
        openings=(),
        rooms=(),
    )
    fields.update(overrides)
    return ResolvedModel(**fields)


def test_fixture_has_no_geometry_errors(fixture_path) -> None:
    model, diagnostics = load_and_validate(fixture_path)
    assert model is not None
    assert all(d.severity != "error" for d in diagnostics)


def test_all_example_fixtures_validate_cleanly(all_example_paths) -> None:
    assert all_example_paths, "expected at least one example fixture"
    for path in all_example_paths:
        model, diagnostics = load_and_validate(path)
        assert model is not None, f"{path}: failed to resolve"
        assert all(d.severity != "error" for d in diagnostics), f"{path}: {diagnostics}"


def test_gruszowa_room_areas_match_source_export(gruszowa_fixture_path) -> None:
    # dom_viewer.html's embedded projectData reports axis-based room areas
    # (_pole_osiowe) of 45.61 m^2 (garaz) and 10.85 m^2 (pom_gosp); this
    # checks the reverse-engineered fixture reproduces that geometry.
    from shapely.geometry import Polygon

    model, _ = load_and_validate(gruszowa_fixture_path)
    areas = {room.id: Polygon(room.outline).area / 10000 for room in model.rooms}

    assert areas["garaz"] == pytest.approx(45.61, abs=0.1)
    assert areas["pom_gosp"] == pytest.approx(10.85, abs=0.1)


def test_minimal_valid_model_has_no_diagnostics() -> None:
    room = ResolvedRoom(
        id="r1", name="Room", floor="wood", floor_color="#d9bd95",
        outline=((100.0, 0.0), (900.0, 0.0), (900.0, 900.0), (100.0, 900.0)),
    )
    opening = ResolvedOpening(id="o1", type="door", p_from=(100.0, 0.0), p_to=(200.0, 0.0), sill=0.0, height=200.0)
    model = _base_model(rooms=(room,), openings=(opening,))

    assert validate_geometry(model) == []


def test_self_intersecting_room_polygon_is_rejected() -> None:
    bowtie = ((0.0, 0.0), (100.0, 100.0), (100.0, 0.0), (0.0, 100.0))
    room = ResolvedRoom(id="bow", name="Bowtie", floor="wood", floor_color="#d9bd95", outline=bowtie)
    model = _base_model(rooms=(room,))

    diagnostics = validate_geometry(model)
    assert any("Room 'bow'" in str(d) and "not a valid polygon" in str(d) for d in diagnostics)


def test_room_outside_outline_is_rejected() -> None:
    room = ResolvedRoom(
        id="out", name="Outside", floor="wood", floor_color="#d9bd95",
        outline=((1100.0, 1100.0), (1300.0, 1100.0), (1300.0, 1300.0), (1100.0, 1300.0)),
    )
    model = _base_model(rooms=(room,))

    diagnostics = validate_geometry(model)
    assert any("Room 'out'" in str(d) and "lies outside the building outline" in str(d) for d in diagnostics)


def test_room_area_not_less_than_outline_is_rejected() -> None:
    room = ResolvedRoom(id="whole", name="Whole", floor="wood", floor_color="#d9bd95", outline=OUTLINE)
    model = _base_model(rooms=(room,))

    diagnostics = validate_geometry(model)
    assert any("total room area" in str(d) for d in diagnostics)


def test_opening_not_on_any_wall_is_rejected() -> None:
    opening = ResolvedOpening(id="floating", type="window", p_from=(500.0, 500.0), p_to=(600.0, 500.0), sill=90.0, height=140.0)
    model = _base_model(openings=(opening,))

    diagnostics = validate_geometry(model)
    assert any("Opening 'floating'" in str(d) and "does not lie on the axis of any wall" in str(d) for d in diagnostics)


def test_opening_sill_plus_height_exceeds_ceiling_is_rejected() -> None:
    opening = ResolvedOpening(id="too_tall", type="window", p_from=(100.0, 0.0), p_to=(200.0, 0.0), sill=200.0, height=100.0)
    model = _base_model(openings=(opening,))

    diagnostics = validate_geometry(model)
    assert any("Opening 'too_tall'" in str(d) and "exceeds ceiling height" in str(d) for d in diagnostics)


def test_pipeline_raises_on_invalid_model(fixture_path, fixture_data) -> None:
    import copy

    import yaml

    data = copy.deepcopy(fixture_data)
    data["openings"][0]["from"] = "P999"
    bad_path = fixture_path.parent / "_bad_fixture_for_test.yaml"
    bad_path.write_text(yaml.safe_dump(data), encoding="utf-8")
    try:
        try:
            load_and_validate(bad_path)
            raised = False
        except ArchtoolValidationError:
            raised = True
        assert raised
    finally:
        bad_path.unlink(missing_ok=True)
