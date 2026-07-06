# archtool geometry language — Language Card (v2 draft)

Everything needed to read or write a valid geometry.yaml. One page.
Normative details: SPEC.md. Machine schema: `archtool schema`.

## Model in one paragraph

A building is a **shell** (closed exterior loop per level) plus interior
**walls**. Walls and shell edges host **openings**. The compiler derives
enclosed **regions** from shell + walls; a **room** is a name claimed on
one region by a seed point. Units are **cm**, integers preferred. Y grows
**downward** (screen convention). Angles in degrees, clockwise.

## Positions — the four ways to say "where"

| Form | Example | Meaning |
|---|---|---|
| grid ref | `2A` | intersection of grid x-line "2" and y-line "A" |
| raw | `[350, 420]` | absolute cm coordinates |
| on-anchor | `{ on: w1, at: 300 }` | point 300 cm along element `w1` from its `from` end |
| (openings only) | `at: 480` | offset of opening start along its host |

Any field expecting a position accepts any applicable form.

## Top-level sections (all optional except building + shell)

```yaml
building:   { name: str, format_version: "2.0" }
grid:       { x: { "1": 0, "2": 350 }, y: { "A": 0, "B": 420 } }
levels:     [ { id: ground, floor_z: 0, ceiling_height: 280 } ]
defaults:   # profiles; referenced by name, overridable per element
  exterior_wall: { thickness: 30 }
  partition:     { thickness: 12 }
  door:          { width: 90, height: 205, sill: 0 }
  window:        { width: 120, height: 150, sill: 90 }
shell:
  <level_id>:
    outline: [1A, 4A, 4C, 1C]      # ≥3 corners, auto-closing, clockwise
    wall: exterior_wall             # profile name or inline { thickness: … }
walls:      [ …see Wall… ]
openings:   [ …see Opening… ]
rooms:      [ …see Room… ]
```

## Wall

```yaml
- id: w_bedroom            # unique across walls
  level: ground            # default: the only level, if single-level
  from: 2A                 # position
  to: { on: shell.1C-1A, at: 350 }
  type: partition          # load_bearing | partition (default: partition)
  thickness: 12            # default: from type profile in defaults:
  justify: center          # center | left | right — which side of the
                           # axis the thickness sits (left/right relative
                           # to from→to direction). Default: center.
```

Geometry meaning: `from`→`to` is the wall **axis**; thickness extends per
`justify`. Shell edges are implicit walls named `shell.<c1>-<c2>` by
their corners, in outline direction.

## Opening

```yaml
- id: entrance
  in: shell.1A-4A          # host: wall id or shell edge id
  at: 480                  # cm from host's from-end to opening START
  type: door               # door | window | garage_gate | empty_space
  width: 100               # default from type profile
  height: 205              # vertical size of the cut
  sill: 0                  # cut starts this far above floor_z
  hinge: start             # doors only: start | end (which jamb)
  swing: in                # doors only: in | out
```

Rules: `at ≥ 0`, `at + width ≤ host length`, openings on one host may not
overlap, `sill + height ≤ ceiling_height`. The cut goes through the full
wall thickness. `in` side of a swing = toward the room whose seed is on
the left of host direction (SPEC defines precisely).

## Room

```yaml
- id: living
  name: "Living room"
  seed: 3B                 # any position strictly inside ONE region
```

Rooms never define geometry. The compiler polygonizes shell + wall axes
into regions; each seed claims the region containing it. Two seeds in one
region = error. Regions without seeds = info diagnostic. Derived outputs
per room (see `archtool resolve`): polygon (inner wall faces), net area,
perimeter, adjacent walls, openings facing the room.

## Identifiers & references

ids: `[a-z][a-z0-9_]*`, unique within their section. Cross-references are
by id and checked; unknown id, unknown field, or wrong type = compile
error naming the element. Grid labels are free strings (`"2"`, `"8a"`).

## Minimal valid file (a 6×4 m box with a door)

```yaml
building: { name: "Box", format_version: "2.0" }
levels:   [ { id: ground, ceiling_height: 280 } ]
shell:
  ground:
    outline: [[0,0], [600,0], [600,400], [0,400]]
    wall: { thickness: 30 }
openings:
  - { id: d1, in: shell.[0,0]-[600,0], at: 250, type: door }
rooms:
  - { id: main, name: "Main room", seed: [300, 200] }
```

## Invariants (what the validator guarantees)

1. Shell outlines are simple (non-self-intersecting) closed polygons.
2. Wall endpoints resolve; axes may only touch at shared endpoints or
   valid T-junctions (`on:` anchors).
3. Openings fit their host, don't overlap siblings, fit under ceiling.
4. Every seed lands in exactly one region.
5. Same file → byte-identical resolved model and outputs.

## CLI verbs

`archtool validate f.yaml` · `archtool build f.yaml --backend svg|gltf`
· `archtool resolve f.yaml` (derived model as JSON — inspect computed
rooms, lengths, areas) · `archtool schema` (JSON Schema) ·
`archtool migrate v1.yaml` (v1 point-format → v2).
