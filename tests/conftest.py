from __future__ import annotations

from pathlib import Path

import pytest
import yaml

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
FIXTURE_PATH = EXAMPLES_DIR / "example_house" / "dom_dane.yaml"
GRUSZOWA_FIXTURE_PATH = EXAMPLES_DIR / "czest_gruszowa_60" / "dom_dane.yaml"


@pytest.fixture
def fixture_path() -> Path:
    return FIXTURE_PATH


@pytest.fixture
def fixture_data() -> dict:
    return yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def gruszowa_fixture_path() -> Path:
    return GRUSZOWA_FIXTURE_PATH


@pytest.fixture
def all_example_paths() -> list[Path]:
    return sorted(EXAMPLES_DIR.glob("*/dom_dane.yaml"))
