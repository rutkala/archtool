# Skill: add-backend

Add a new output format backend to archtool. Backends are isolated plugins:
they read the `ResolvedModel` and write one output format. Adding a backend
must not touch the parser, resolver, or any other backend.

## Architecture constraint

`ResolvedModel` (in `src/archtool/resolved.py`) is the **only** input to any
backend. Never read the raw YAML or `BuildingFile` from a backend.

## Checklist

### 1. Create the backend module (`src/archtool/backends/<format>.py`)
Implement a top-level function:
```python
def render_<format>(model: ResolvedModel, output_path: Path) -> None: ...
```
Mirror the structure of `src/archtool/backends/svg.py`:
- Pure function, no side effects beyond writing the file.
- Deterministic output (same input → same bytes where the format allows).

### 2. Wire it into the CLI (`src/archtool/cli.py`)
In the `build` command, add the new format to the `--format` option and import
+ call your `render_<format>` function. Pattern: copy how SVG is handled.

### 3. Add a test (`tests/test_<format>.py` or extend `test_cli.py`)
At minimum: call `render_<format>` on both fixtures and assert the output file
exists and is non-empty. If the format is text-based, assert it contains the
building name or a known room id.

### 4. Update SPEC.md if the format has interpretation choices
If the new format requires decisions (e.g. Y-axis flip for glTF), document them
in SPEC.md §1.1 or add a new section.

### 5. Run the full test suite
```
.venv\Scripts\python.exe -m pytest tests/ -q
```
All tests must pass before committing.
