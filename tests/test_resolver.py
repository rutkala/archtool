from __future__ import annotations

import copy

from archtool.models import BuildingFile
from archtool.resolver import parse_schema, resolve


def test_resolve_fixture_succeeds(fixture_data: dict) -> None:
    bf = parse_schema(fixture_data)
    model, diagnostics = resolve(bf)

    assert model is not None
    assert diagnostics == []
    assert len(model.outline) == len(fixture_data["outline"])
    assert len(model.rooms) == len(fixture_data["rooms"])
    assert len(model.walls) == len(fixture_data["walls"])
    assert len(model.openings) == len(fixture_data["openings"])


def test_exterior_walls_derived_from_outline(fixture_data: dict) -> None:
    bf = parse_schema(fixture_data)
    model, _ = resolve(bf)

    assert model is not None
    assert len(model.exterior_walls) == len(fixture_data["outline"])
    thickness = fixture_data["building"]["exterior_wall_thickness"]
    assert all(w.thickness == thickness for w in model.exterior_walls)
    assert all(w.type == "load_bearing" for w in model.exterior_walls)


def test_missing_point_name_reports_diagnostic_with_suggestion(fixture_data: dict) -> None:
    data = copy.deepcopy(fixture_data)
    data["walls"][0]["from"] = "P999"  # not in points:, but close to nothing in particular

    bf = parse_schema(data)
    model, diagnostics = resolve(bf)

    assert model is None or any(d.severity == "error" for d in diagnostics)
    messages = [str(d) for d in diagnostics]
    assert any("P999" in m and "not found in points" in m for m in messages)


def test_missing_point_name_suggests_close_match(fixture_data: dict) -> None:
    data = copy.deepcopy(fixture_data)
    data["openings"][0]["from"] = "P211"  # typo of P21

    bf = parse_schema(data)
    _, diagnostics = resolve(bf)

    messages = [str(d) for d in diagnostics]
    assert any("did you mean 'P21'" in m for m in messages)


def test_unknown_field_rejected_by_schema(fixture_data: dict) -> None:
    data = copy.deepcopy(fixture_data)
    data["building"]["unexpected_field"] = "surprise"

    try:
        BuildingFile.model_validate(data)
        raised = False
    except Exception:
        raised = True
    assert raised
