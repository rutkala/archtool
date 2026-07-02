# Skill: add-opening-type

Add a new opening type to archtool. Opening types control how a gap in a wall is
drawn in the SVG (door swing, window pane, gate slab, empty gap). The type never
affects the cut geometry — only the drawing.

## Checklist

### 1. Register the type in the model (`src/archtool/models.py`)
Add the new string literal to the `Literal` union in `Opening.type`.

### 2. Handle it in the SVG backend (`src/archtool/backends/svg.py`)
Inside `_render_opening()`, add an `elif opening.type == "<new_type>":` branch.
Return a list of SVG element strings. Follow the existing branches as patterns:
- `door` — swing arc + leaf line
- `window` — two parallel lines (panes)
- `garage_gate` — bar with end ticks
- `empty_space` — returns `[]` (nothing drawn across the gap)

The helper `_wall_cut_corners()` gives you the four corners of the opening
rectangle in wall-perpendicular/wall-parallel coordinates.

### 3. Update the fixture (`examples/czest_gruszowa_60/dom_dane.yaml`)
Add at least one opening of the new type so it is exercised against real geometry.

### 4. Update SPEC.md §5
Add a bullet describing what the new type looks like and when to use it.

### 5. Add a test (`tests/test_svg.py`)
Add a test that calls `render_svg` on the Gruszowa fixture and asserts the new
opening appears in the SVG output (search for a distinctive element string). At
minimum, verify the SVG is valid XML and the opening id appears.

### 6. Run the full test suite
```
.venv\Scripts\python.exe -m pytest tests/ -q
```
All tests must pass before committing.
