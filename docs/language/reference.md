# archtool Geometry Language — Reference (v2.0-draft.2)

This is the complete authoring reference for `geometry.yaml`. It documents
every section, every field, every value form, and every validation rule of
the draft language. If something is not in this document, it is not part
of the language (yet) — see §14 for known future extensions.

Reading order for first-time authors: §1 mental model → §2 data types →
§13 worked example → then the section references (§4–§11) as needed.

Status: **draft**. The language is being developed corpus-first; this
document is the contract the corpus is written against, and it changes
via versioned revisions as corpus writing exposes problems (see §15 for
the revision history).

---

## 1. Mental model

A building is described by declaring, per level:

1. a **shell** — one closed exterior loop of thick walls,
2. interior **walls** — straight segments with thickness,
3. **openings** — doors/windows cut into shell edges or walls,
4. **rooms** — names claimed on the enclosed regions that shell + walls
   produce. Rooms are *derived*: you never draw a room boundary.

You describe **intent** ("a 100 cm door in the south shell edge, 480 cm
from the west corner"); the compiler computes all resulting geometry
(the *resolved model*: exact polygons, areas, cut solids), which you can
inspect with `archtool resolve`.

**Conventions (fixed):**
- Units: **centimeters**, integers preferred (floats allowed).
- Axes: X grows right, **Y grows up** — north-up, the map/architect
  convention. Flipping to screen coordinates is the rendering backend's
  job (e.g. SVG), never the author's. The origin is arbitrary — pick
  anything; only relative positions matter.
- Plans are described in 2D; height enters via `levels` (floor_z,
  ceiling_height) and opening `sill`/`height`.
- YAML: block style and flow style (`{ }`, `[ ]`) are equivalent.
  Unknown fields are **errors** (strict schema — protects against typos).

---

## 2. Data types

### 2.1 `position`
Anywhere a point is expected, three forms are accepted:

| Form | Syntax | Example | Meaning |
|---|---|---|---|
| grid ref | `"<x-label><y-label>"` or dot form `"<x-label>.<y-label>"` | `"2A"`, `"8a.D"` | intersection of grid lines |
| raw | `[x, y]` | `[350, 420]` | absolute coordinates in cm |
| anchor | `{ on: <element>, at: <number> }` | `{ on: w1, at: 300 }` | point on an element's axis, `at` cm from its `from` end |

Anchor targets: a wall id, or a shell edge id (§8.3). `at` must be within
`[0, length]` of the target.

The dot form of a grid ref is always allowed and is **required** where
terse concatenation is ambiguous — see §5.

### 2.2 `grid-label`
Any string: `"1"`, `"2"`, `"8a"`, `"kitchen-axis"`. Quoting numeric
labels is required (`"1"`), otherwise YAML reads them as numbers.

### 2.3 `id`
Pattern `[a-z][a-z0-9_]*`. Unique within its section (walls, openings,
rooms, corners each have their own namespace).

### 2.4 `profile`
A named bundle of defaults defined under `defaults:` (§7). Fields taking
a profile accept the profile name (string) or an inline object; inline
fields override profile fields.

---

## 3. File anatomy

```yaml
building:   # required — identity & language version
status:     # required — draft | reviewed (§3.1)
grid:       # optional — named reference lines
levels:     # required — at least one storey
defaults:   # optional — profiles for walls/openings
shell:      # required — exterior envelope per level
walls:      # optional — interior walls
openings:   # optional — doors, windows, cuts
rooms:      # optional — names for enclosed regions
```

### 3.1 `status` — promotion

Every layer file carries a top-level `status` field with exactly two
values: `draft` or `reviewed`. Importers always emit `status: draft`;
`archtool validate` emits a warning for every file still in `draft`;
promotion means editing the field to `reviewed` after review — which
makes every promotion an attributable git change. There are no
registries and no sidecar files. (This reference specifies
`geometry.yaml`; the same field with the same rules appears in every
layer file.)

---

## 4. `building`

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | string | yes | — | Human name of the project/building. |
| `format_version` | string | yes | — | Language version this file targets, e.g. `"2.0"`. The compiler refuses versions it doesn't support. |

No other fields. Addresses, registry ids, owner data belong in
`archtool.yaml` (project config), not in geometry.

---

## 5. `grid`

Optional named reference lines. Vertical lines under `x:` (constant x),
horizontal under `y:` (constant y).

```yaml
grid:
  x: { "1": 0, "2": 350, "3": 650 }
  y: { "A": 0, "B": 420, "C": 700 }
```

| Field | Type | Required | Description |
|---|---|---|---|
| `x` | map grid-label → number | no | label → x coordinate (cm) |
| `y` | map grid-label → number | no | label → y coordinate (cm) |

A grid ref `"2B"` is valid iff `"2"` exists in `x` and `"B"` in `y`.
Terse concatenation (`"2B"`) is the default spelling; the dot-separated
form (`"2.B"`, `"8a.D"`) is always allowed and is **required** when
concatenation would be ambiguous (e.g. x has both `"8"` and `"8a"` while
y has both `"aD"` and `"D"` — `"8aD"` could parse two ways). The
compiler identifies every ambiguous ref and refuses it, naming the dot
form as the fix. Grid lines are reference-only: they render as thin
annotation lines but produce no geometry.

## 6. `levels`

At least one entry. (Multi-level linking — stairs, shafts — is future,
§14; today levels are independent plans.)

```yaml
levels:
  - { id: ground, floor_z: 0, ceiling_height: 280 }
```

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `id` | id | yes | — | Referenced by shell/walls. |
| `floor_z` | number | no | `0` | Absolute height of finished floor. |
| `ceiling_height` | number | yes | — | floor→ceiling clear height (cm). |

If exactly one level exists, `level:` fields elsewhere may be omitted.

## 7. `defaults`

Named profiles. Two profile kinds, distinguished by their fields:

**Wall profile:** `thickness` (number, cm), optional `type`
(`load_bearing` | `partition`).
**Opening profile:** any of `width`, `height`, `sill` (numbers, cm).

```yaml
defaults:
  exterior_wall: { thickness: 30, type: load_bearing }
  partition:     { thickness: 12 }
  door:          { width: 90, height: 205, sill: 0 }
  window:        { width: 120, height: 150, sill: 90 }
```

Profile names are free, but `door`, `window`, `garage_gate`,
`empty_space`, `partition`, `load_bearing` are **auto-applied**: an
opening of `type: window` uses the `window` profile automatically if it
exists; a wall of `type: partition` uses `partition`. Other profiles are
applied by explicit reference.

## 8. `shell`

One entry per level id. The exterior envelope.

```yaml
shell:
  ground:
    outline: [1A, 1C, 4C, 4A]
    wall: exterior_wall
```

| Field | Type | Required | Description |
|---|---|---|---|
| `outline` | list of corner (§8.1), ≥3 | yes | Closed loop, **clockwise as seen on the north-up plan** (Y grows up, §1), auto-closing (do not repeat the first corner). |
| `wall` | profile | yes | Thickness (+type) of the envelope walls. |
| `edges` | map id → [corner-name, corner-name] | no | Friendly aliases for edges (§8.3). |

### 8.1 Corners
A corner is a `position`, or a named corner `{ id: <id>, at: <position> }`:

```yaml
outline:
  - 1A                      # grid ref (its own name is "1A")
  - 1C
  - [900, 600]              # raw, unnamed
  - { id: se, at: [900, 0] }  # raw position with a name
```

### 8.2 Geometry
Corner positions define the shell **axis polygon** (wall centerlines).
Thickness extends half-in/half-out of the axis by default. Per-edge
`justify` overrides are future (§14); v2.0 shells are center-justified.

### 8.3 Edge ids
Every edge gets an automatic id `shell.<from>-<to>` from its corner
names in outline order, e.g. `shell.1A-1C`, `shell.se-1A`. Unnamed raw
corners produce unreferenceable edges — name the corner if you need its
edge (this is deliberate: it keeps references readable). The `edges:`
map adds aliases: `edges: { south: [4A, 1A] }` makes `shell.south` valid.

## 9. `walls`

Interior walls. Straight segments only (curves: §14).

```yaml
walls:
  - id: w_bedroom
    level: ground
    from: 2A
    to: { on: shell.1C-1A, at: 350 }
    type: partition
    thickness: 12
    justify: center
```

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `id` | id | yes | — | |
| `level` | level id | if >1 level | the only level | |
| `from`, `to` | position | yes | — | Wall **axis** endpoints. |
| `type` | `load_bearing` \| `partition` | no | `partition` | Also selects auto-profile. |
| `thickness` | number | no | from profile | cm. |
| `justify` | `center` \| `left` \| `right` | no | `center` | Which side of the axis the body occupies; left/right relative to `from`→`to` direction. Use to keep faces flush. |

**Junction rules:** wall axes may meet at shared endpoints, or in a
T-junction. A T-junction is expressed in either of two equivalent ways:
the joining wall's endpoint is an anchor `{ on: <other>, at: … }`, or
its endpoint (grid ref or raw) resolves to a position lying **exactly**
on the other wall's axis. Exactly means exactly — near-misses are not
snapped; a wall that stops a few cm short leaves a sliver region (W02).
Axes that cross anywhere else are an error (split the wall at the
crossing point). Endpoints on a shell edge work the same way: an anchor
on that edge, or a grid ref / raw position lying exactly on it. A wall
endpoint that touches nothing at all is reported as W04 "free-standing
wall end" (informational).

## 10. `openings`

```yaml
openings:
  - id: entrance
    in: shell.1A-4A
    at: 480
    type: door
    width: 100
    hinge: start
    swing: in
```

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `id` | id | yes | — | |
| `in` | wall id or shell edge id | yes | — | Host element. |
| `at` | number \| `center` | yes | — | Position along the host axis, measured from the host's `from` end (for shell edges: the first corner in outline order). Three forms — see below. |
| `type` | `door` \| `window` \| `garage_gate` \| `empty_space` | yes | — | `empty_space` = open pass-through, no joinery drawn. |
| `width` | number | from profile | — | Along the host. |
| `height` | number | from profile | — | Vertical size of cut. |
| `sill` | number | from profile | `0` | Cut bottom above `floor_z`. Doors/gates: must be `0`. |
| `hinge` | `start` \| `end` | doors only | `start` | Jamb carrying the hinge (`start` = the jamb nearer the host's `from` end). |
| `swing` | `in` \| `out` | doors only | `in` | `in` = swings toward the region on the **left** of the host's from→to direction. |

`at` accepts three forms:

- **non-negative number** — cm from the host's start to the opening's
  **start edge** (the jamb nearer the host's start).
- **negative number** — mirror of the positive form: cm from the host's
  **end** to the opening's **end edge**. `at: -60` leaves a 60 cm pier
  between the opening and the host's end (start edge =
  `length − |at| − width`).
- **`center`** — the opening is centered on the host's midpoint
  (start edge = `(length − width) / 2`).

Whatever the form, the resolved span `[start, start + width]` must lie
within `[0, length]` of the host (E06).

The cut always goes through the full host thickness.

## 11. `rooms`

```yaml
rooms:
  - { id: living, name: "Living room", seed: 3B }
```

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | id | yes | |
| `name` | string | yes | Display label. |
| `level` | level id | if >1 level | |
| `seed` | position | yes | Any point strictly inside exactly one enclosed region — pick roughly the middle; it has no geometric meaning beyond region selection. |

Derived per room (see `archtool resolve`): boundary polygon at inner
wall faces, net floor area, perimeter, bounding walls, openings.

## 12. Validation rules

**Errors** (build refused): E01 unknown field / bad type / bad id ·
E02 unresolvable reference (grid ref, profile, anchor target, level) ·
E03 shell outline not simple or < 3 corners · E04 wall zero-length ·
E05 wall axes crossing outside endpoints/T-junctions · E06 opening
outside host (resolved span `[start, start+width]` not within
`[0, length]`) · E07 openings
overlapping on one host · E08 `sill + height > ceiling_height` · E09
door/gate with `sill ≠ 0` · E10 room seed in no region / on a boundary ·
E11 two seeds in one region.

**Warnings:** W01 region with no room claiming it · W02 sliver region
(< 1 m²) — usually a wall meant to touch but missing by a few cm · W03
wall thicker than its length · W04 free-standing wall end — a wall
endpoint that meets no wall endpoint, wall axis, or shell edge
(informational: legitimate for a deliberate wall stub, but often a
missed connection).

`archtool validate` additionally warns for every file with
`status: draft` (§3.1); this is a file-level notice, not a numbered
geometry diagnostic.

Every diagnostic names the element id and states the fix direction.

## 13. Worked example — L-shaped bungalow, complete file

```yaml
building: { name: "L-bungalow", format_version: "2.0" }
status: draft        # promote to `reviewed` after review (§3.1)

grid:
  x: { "1": 0, "2": 420, "3": 780, "4": 1150 }
  y: { "A": 0, "B": 450, "C": 800 }

levels: [ { id: ground, ceiling_height: 275 } ]

defaults:
  exterior_wall: { thickness: 30, type: load_bearing }
  partition:     { thickness: 12 }
  door:          { width: 90, height: 205, sill: 0 }
  window:        { width: 140, height: 150, sill: 85 }

shell:
  ground:
    outline: [1A, 1C, 2C, 2B, 4B, 4A]     # the L — clockwise, north-up (Y grows up)
    wall: exterior_wall
    edges: { south: [4A, 1A], west: [1A, 1C] }

walls:
  - { id: w_bed,  from: 2A, to: 2B, type: load_bearing, thickness: 25 }
  - { id: w_bath, from: { on: w_bed, at: 260 }, to: { on: shell.west, at: 260 },
      type: partition }

openings:
  - { id: entrance,  in: shell.south,  at: 490,    type: door, width: 100, swing: in }
  - { id: w_living1, in: shell.4B-4A,  at: center, type: window, width: 200 }
  - { id: w_bed1,    in: shell.west,   at: 400,    type: window }
  - { id: w_kitchen, in: shell.2B-4B,  at: -60,    type: window }
  - { id: d_bed,     in: w_bed,        at: 300,    type: door, hinge: end }
  - { id: d_bath,    in: w_bath,       at: 40,     type: door, width: 80 }

rooms:
  - { id: living,  name: "Living + kitchen", seed: [780, 220] }   # east wing, ≈ middle
  - { id: bedroom, name: "Bedroom",          seed: [200, 500] }
  - { id: bath,    name: "Bathroom",         seed: [200, 120] }
```

Reading check: `w_bath` runs from a T-junction on `w_bed` (260 cm along
its axis) to an anchor on the west shell edge; `w_living1` sits centered
on the east edge (`at: center`) and `w_kitchen` holds a 60 cm pier to
the corner (`at: -60`) — no coordinates computed by hand anywhere in the
file except the three room seeds.

## 14. Not in the language yet (do not use)

Multi-level connections (stairs, voids) · curved/angled-thickness walls ·
per-edge shell justify · sloped ceilings/roofs · columns · wall layers
(construction build-ups) · site/terrain. Each will arrive as a versioned
language revision with migration notes.

## 15. Revision history

- **v2.0-draft.2** (2026-07-06) — folds in decision-log entries D12,
  D15, D17:
  - Y axis grows **up** (north-up, map/architect convention); flipping
    to screen coordinates is the rendering backend's job (D15a). All
    examples re-authored Y-up.
  - Grid refs: dot-separated form (`"8a.D"`) always allowed, required
    where terse concatenation is ambiguous; the compiler identifies
    such refs (D15b).
  - Opening `at` accepts non-negative number / negative
    number-from-end / `center` (D15c); E06 restated over the resolved
    span.
  - T-junction expressible by an endpoint lying exactly on another
    wall's axis, equivalent to the anchor form (D12a).
  - New informational diagnostic W04 "free-standing wall end" (D12b).
  - Top-level `status: draft | reviewed` promotion field on every layer
    file; `validate` warns on drafts (D17).
- **v2.0-draft.1** — initial complete reference.

---

*Docs discipline: every YAML block in this file must compile (CI runs
them); every rule E/W-number must map to one validator test. Revision
history: §15 above.*
