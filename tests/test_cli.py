from __future__ import annotations

import copy

import yaml
from typer.testing import CliRunner

from archtool.cli import app

runner = CliRunner()


def test_cli_validate_succeeds_on_fixture(fixture_path) -> None:
    result = runner.invoke(app, ["validate", str(fixture_path)])

    assert result.exit_code == 0
    assert "OK:" in result.stdout


def test_cli_validate_succeeds_on_all_example_fixtures(all_example_paths) -> None:
    assert all_example_paths, "expected at least one example fixture"
    for path in all_example_paths:
        result = runner.invoke(app, ["validate", str(path)])
        assert result.exit_code == 0, f"{path}: {result.output}"


def test_cli_build_succeeds_on_gruszowa_fixture(gruszowa_fixture_path, tmp_path) -> None:
    out_path = tmp_path / "gruszowa.svg"

    result = runner.invoke(app, ["build", str(gruszowa_fixture_path), "--out", str(out_path)])

    assert result.exit_code == 0
    assert out_path.exists()
    assert "Garage" in out_path.read_text(encoding="utf-8")


def test_cli_validate_fails_with_precise_error(fixture_data, tmp_path) -> None:
    data = copy.deepcopy(fixture_data)
    data["walls"][0]["from"] = "P999"
    bad_path = tmp_path / "bad.yaml"
    bad_path.write_text(yaml.safe_dump(data), encoding="utf-8")

    result = runner.invoke(app, ["validate", str(bad_path)])

    assert result.exit_code == 1
    assert "P999" in result.output
    assert "not found in points" in result.output


def test_cli_build_writes_svg(fixture_path, tmp_path) -> None:
    out_path = tmp_path / "plan.svg"

    result = runner.invoke(app, ["build", str(fixture_path), "--out", str(out_path)])

    assert result.exit_code == 0
    assert out_path.exists()
    assert out_path.read_text(encoding="utf-8").startswith("<svg")


def test_cli_build_fails_on_invalid_file(fixture_data, tmp_path) -> None:
    data = copy.deepcopy(fixture_data)
    data["rooms"][0]["outline"] = ["P1"]  # fewer than 3 points
    bad_path = tmp_path / "bad.yaml"
    bad_path.write_text(yaml.safe_dump(data), encoding="utf-8")

    result = runner.invoke(app, ["build", str(bad_path), "--out", str(tmp_path / "out.svg")])

    assert result.exit_code == 1
    assert not (tmp_path / "out.svg").exists()


def test_cli_init_creates_project_directory(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["init", "myhouse"])

    assert result.exit_code == 0
    project_dir = tmp_path / "myhouse"
    assert (project_dir / "dom_dane.yaml").exists()
    assert (project_dir / "README.md").exists()
    assert "myhouse" in (project_dir / "dom_dane.yaml").read_text(encoding="utf-8")


def test_cli_init_starter_project_validates_and_builds(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "myhouse"])
    starter = tmp_path / "myhouse" / "dom_dane.yaml"

    validate_result = runner.invoke(app, ["validate", str(starter)])
    assert validate_result.exit_code == 0, validate_result.output

    build_result = runner.invoke(app, ["build", str(starter)])
    assert build_result.exit_code == 0, build_result.output
    assert (tmp_path / "myhouse" / "dom_dane.svg").exists()


def test_cli_init_fails_if_directory_already_exists(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "myhouse").mkdir()

    result = runner.invoke(app, ["init", "myhouse"])

    assert result.exit_code == 1
    assert "already exists" in result.output
    assert not (tmp_path / "myhouse" / "dom_dane.yaml").exists()
