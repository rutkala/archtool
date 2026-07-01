# SPEC.md — Building specification format (version 1.0)

This document is the **interpretation contract** for `dom_dane.yaml`. It defines
how the data (geometry) is turned into a 2D/3D model so that any tool or model
produces the **same geometric result**. A data file declares conformance via
`building.format_version` and `building.spec`.

Everything here — and in the data files — is in **English**.

---

## 1. Units and coordinate system

- All coordinates are in **centimetres (cm)**.
- The point **(0, 0)** is the top-left corner of the plan.
- **X increases to the right →**.
- **Y increases downward ↓** (plan north is up; this is a screen convention, not
  a geographic one).
- Every point is written as `[x, y]`.

### 1.1 Converting to Y-up systems
When exporting to formats where Y increases upward (glTF, DXF, most 3D):
```
x_out = x_in
y_out = -y_in        (or: y_out = H - y_in, where H = max y of the outline)
```
The building's vertical extent becomes the Z axis.

---

## 2. Points

Points can be defined in two places:

### 2a. Inline in `outline:` (perimeter points)

Perimeter corners are defined directly inside the `outline:` list — no
separate `points:` entry is needed for them. Each entry is:

```yaml
- id: P1        # unique name referenced everywhere else
  x: 0          # x coordinate in cm
  y: 0          # y coordinate in cm
  x_axis: "1"   # optional: names the vertical gridline at this x value
  y_axis: "A"   # optional: names the horizontal gridline at this y value
```

`x_axis` and `y_axis` are **optional**. When present they label the
architectural reference grid (see §2b). The same label must not appear at
two different coordinate values — that is an error.

### 2b. In `points:` (non-perimeter points)

All other named coordinates — interior T-junction points, opening
endpoints, etc. — go in the optional `points:` section as before:

```yaml
points:
  D1a: [50, 0]
  D1b: [150, 0]
```

A name appearing in both `outline:` (as an `id`) and `points:` is an error.
The resolver merges both sources into a single point namespace before
resolving any name reference. A name used anywhere that is not found in
either source is an error.

---

## 3. Building outline (`outline:`)

- A list of **inline point definitions** (see §2a) in perimeter order (clockwise).
- The polygon **closes automatically**: the last point connects to the first.
  Do not repeat the first point at the end.
- Area via the shoelace formula; cm² ÷ 10000 = m².

### 3.1 Architectural grid axes

When outline points carry `x_axis` / `y_axis` labels the SVG backend
draws a dashed reference gridline for each distinct label:

- `x_axis: "N"` → a vertical dashed line at that x coordinate, labelled
  "N" in a circle bubble above the building.
- `y_axis: "L"` → a horizontal dashed line at that y coordinate, labelled
  "L" in a circle bubble to the left of the building.

Gridlines are drawn behind all geometry (behind rooms and walls) so they
never obscure the plan. A label declared on multiple outline points is
accepted only if every occurrence has the same coordinate value.

---

## 4. Walls (`walls:`)

Each wall is a segment between two points (`from`, `to`) with attributes.

- The `from`–`to` line is the wall **axis** (reference line).
- `thickness` is the wall's thickness, in cm. **Optional** — when omitted
  the resolver fills in `building.exterior_wall_thickness` for
  `load_bearing` walls and `building.partition_wall_thickness` for
  `partition` walls.
- `justify` (optional, default `"center"`): how `thickness` is distributed
  relative to the axis, perpendicular to the wall direction:
  - `"center"` — split half on each side (±thickness/2). Default.
  - `"left"` / `"right"` — the full thickness on one side, the axis becomes
    that face's *opposite* edge. Defined relative to the direction of
    travel from `from` to `to`: walking from `from` toward `to`, `"left"`
    puts all the material on your left-hand side, `"right"` on your
    right-hand side.

  Use `"left"`/`"right"` so two colinear walls of *different* thickness can
  share one face flush, without needing separate points for each wall —
  both walls still connect at the exact same named point. Centering walls
  of different thickness on the same axis point is valid but leaves their
  faces offset by half the thickness difference on each side; that is a
  deliberate design choice (a visible step), not an error.
- `type`: `"load_bearing"` or `"partition"` — affects default thickness and
  drawing style, not the axis geometry.
- Exterior walls come from `outline:` with thickness
  `building.exterior_wall_thickness`, always `"center"`-justified; walls in
  `walls:` are interior walls.

---

## 5. Openings (`openings:`)

Each opening lies on the axis of some wall.

- `from`, `to`: points giving the **width** of the opening along the wall axis.
- `type`: `"door"`, `"window"`, `"garage_gate"`, or `"empty_space"`.
  - `"door"` — drawn with a leaf and a quarter-circle swing arc (radius =
    opening width, hinged at `from`).
  - `"window"` — drawn as two parallel lines across the wall thickness (the
    panes); no leaf.
  - `"garage_gate"` — a vehicle door: drawn as a single bar across the
    opening with short end ticks (the closed door slab), not a swing —
    garage doors don't swing into the room like a hinged door.
  - `"empty_space"` — an open structural pass-through with no door leaf at
    all: just the gap in the wall, nothing drawn across it. Use this for
    wide openings that aren't actually a door (e.g. an archway) — forcing
    a swing-door symbol onto an opening much wider than a real door leaf
    produces a swing arc as wide as the opening, which doesn't represent
    anything real.
  - All four share the same geometry rules below (`sill`/`height`/wall-axis
    placement) — `type` only changes how the opening is drawn, never the
    cut itself.
- `sill`: height of the opening's bottom edge above the room floor, in cm.
  Doors, garage gates, and empty-space openings use `sill: 0`.
- `height`: opening height in cm (bottom edge to top edge).
- In 3D the opening **cuts** a rectangle from the wall solid: from `sill` to
  `sill + height`, through the full wall thickness, over the `from`–`to` width.
- `sill + height` must not exceed `building.ceiling_height`.

---

## 6. Rooms (`rooms:`)

- Each room is a closed polygon (`outline:` as a list of point names).
- Closes automatically (like the building outline).
- `floor`: one of the values mapped in §7.
- Area via the shoelace formula, in m².
- Room polygons describe the **interior** (approximation along wall axes; exact
  net area may account for wall thicknesses if a tool chooses to).

---

## 7. Floor material → colour mapping

For consistent 2D/3D visualisation:

| floor      | colour (hex) | description        |
|------------|--------------|--------------------|
| `wood`     | `#d9bd95`    | plank / board      |
| `tiles`    | `#d8d4cb`    | ceramic tiles      |
| `laminate` | `#c9a872`    | laminate panels    |
| `concrete` | `#9a9a93`    | concrete / garage  |
| `carpet`   | `#b7a8a0`    | carpet             |

---

## 8. Height (3D)

- Walls extrude from floor (z=0) to `building.ceiling_height` (z=H).
- A room floor is its polygon at z=0.
- Openings are cut per §5.

---

## 9. Deterministic ordering (optional)

So output is identical in ordering across tools:
- Emit points in ascending name order (`P1`, `P2`, …).
- Where output format does not require perimeter order, sort result vertices
  ascending by (x, then y).

---

## 10. Geometry validation

1. Every name used in `walls`/`openings`/`rooms` exists in the merged
   point namespace (outline inline ids + `points:` entries). Outline
   point ids must be unique; no id may appear in both sources.
2. Building outline and every room have ≥ 3 points and form valid closed,
   non-self-intersecting polygons.
3. Openings lie on a wall axis, within that wall's span.
4. `sill + height` ≤ `ceiling_height` for every opening.
5. Rooms lie within the building outline.
6. Sum of room areas < outline area (walls occupy space).

---

## 11. Formal rules framework (compliance) — DESIGN, not v0.1

A serious building compiler validates designs against codified standards. This
section defines the *framework*; concrete checks are implemented in a later phase.

### 11.1 Structure
- Rules are grouped into named **rulesets**, selected per project
  (e.g. `pl_wt`, or an international/illustrative set).
- Each rule is a pure function over the resolved model returning
  `pass` / `warning` / `error`, with a human message and a clause reference.
- Two categories:
  - **Code requirements** — legal minimums (hard; violation = error).
  - **Design guidelines** — ergonomic best practice (soft; violation = warning):
    furniture clearances, circulation widths, kitchen work-triangle, daylight, etc.

### 11.2 Seed ruleset `pl_wt` (Polish *Warunki Techniczne*)
Numbers from the Polish building regulation (Rozporządzenie w sprawie warunków
technicznych, jakim powinny odpowiadać budynki i ich usytuowanie). To be
implemented later; documented here so the data model anticipates them.

- Habitable room clear height ≥ **250 cm**; technical/circulation ≥ **220 cm**.
- Door to a habitable room or kitchen ≥ **80 cm** wide, **200 cm** high (in frame).
- Entrance door to a dwelling ≥ **90 cm** wide, **200 cm** high.
- Dwelling usable area ≥ **25 m²**; at least one room ≥ **16 m²**.
- (Site/placement rules — e.g. minimum distance to plot boundary — belong to a
  later, site-aware phase that also ingests the parcel geometry.)

### 11.3 Data the model may need later (anticipate, don't implement in v0.1)
- A room `purpose` (habitable / kitchen / bathroom / technical / circulation)
  so rules can apply selectively.
- Per-opening role (entrance vs internal door) for door-width rules.