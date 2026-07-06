# archtool layered YAML — spec by example

One coherent mini-project: a 9 m × 6 m cottage with a living room and a
bedroom. All five files describe the *same* house, each at its own layer.
Units: cm. Coordinates and conventions follow SPEC (Y down, named points,
walls as axes). Compact flow style (`{ }`) and block style are both valid
YAML — use whichever reads better.

---

## archtool.yaml — project config

```yaml
project: example_cottage
spec_version: "2.0"

layers:
  geometry: geometry.yaml
  semantics: semantics.yaml      # optional — geometry-only projects still compile
  appearance: appearance.yaml    # optional
  products: products.yaml        # optional

rulesets: [geometry, ergonomics] # compliance rulesets (pl_wt) are opt-in

meta:                            # non-geometric registry data lives here now
  building_id: null
  parcel_id: null
  address: null
```

---

## geometry.yaml — Layer 1, pure math

What changed vs v1: no `floor:` on rooms (moved to appearance), no
registry ids in `building:` (moved to archtool.yaml). Everything else is
your current format.

```yaml
building:
  name: "Example cottage"
  ceiling_height: 270
  exterior_wall_thickness: 30
  partition_wall_thickness: 12
  unit: "cm"
  format_version: "2.0"
  spec: "SPEC.md"

outline:                          # perimeter corners, clockwise, auto-closing
  - { id: P1, x: 0,   y: 0,   x_axis: "1", y_axis: "A" }
  - { id: P2, x: 900, y: 0,   x_axis: "3" }
  - { id: P3, x: 900, y: 600, y_axis: "B" }
  - { id: P4, x: 0,   y: 600 }

points:                           # non-perimeter named points
  P5:  [600, 0]                   # partition junction, top
  P6:  [600, 600]                 # partition junction, bottom
  D1a: [250, 600]                 # entrance door endpoints
  D1b: [350, 600]
  W1a: [150, 0]                   # living window
  W1b: [330, 0]
  W2a: [700, 0]                   # bedroom window
  W2b: [820, 0]
  D2a: [600, 250]                 # interior door
  D2b: [600, 340]

walls:                            # interior walls only; exterior comes from outline
  - { id: w1, from: P5, to: P6, type: partition }   # thickness → building default (12)

openings:
  - { id: entrance,   type: door,   from: D1a, to: D1b, sill: 0,  height: 205 }
  - { id: win_living, type: window, from: W1a, to: W1b, sill: 90, height: 150 }
  - { id: win_bed,    type: window, from: W2a, to: W2b, sill: 90, height: 150 }
  - { id: d_bedroom,  type: door,   from: D2a, to: D2b, sill: 0,  height: 205 }

rooms:                            # shape + identity only — no materials here
  - { id: living,  name: "Living room", outline: [P1, P5, P6, P4] }
  - { id: bedroom, name: "Bedroom",     outline: [P5, P2, P3, P6] }
```

---

## semantics.yaml — Layer 2, meaning and placement

References geometry only by **id** (room ids, wall ids, point names).
Exterior wall segments have no id, so they are referenced by their two
outline points: `against: [P4, P1]`.

```yaml
rooms:
  living:
    purpose: habitable            # habitable | kitchen | bathroom | technical | circulation
    zones:
      - id: lounge                # optional sub-areas for layout logic
        area: [[40, 250], [560, 560]]   # axis-aligned rect: [min_xy, max_xy]
  bedroom:
    purpose: habitable

furniture:
  - id: sofa1
    kind: sofa                    # abstract kind from a fixed vocabulary — never a brand
    footprint: [220, 95]          # w × d in cm, before a product is chosen
    height: 85
    room: living
    place: { against: [P4, P1], align: center }
    clearances: { front: 90 }     # validator keeps this strip free

  - id: coffee_table
    kind: table_low
    footprint: [110, 60]
    room: living
    place: { in_front_of: sofa1, gap: 40, align: center }

  - id: bed1
    kind: bed_double
    footprint: [160, 200]
    room: bedroom
    place: { against: [P2, P3], align: center, facing: room }
    clearances: { left: 60, right: 60 }

  - id: wardrobe1
    kind: wardrobe
    footprint: [150, 60]
    room: bedroom
    place: { against: w1, align: start, offset: 20 }   # interior walls by id
```

**Placement primitives** (compiler resolves them to coordinates, like
named points): `against: <wall|[pt,pt]>` + `align: start|center|end` +
`offset: cm`, or `at: [x, y]` + `rotation: deg`, or relational
`in_front_of / beside: <furniture-id>` + `gap`. `facing: room|<point>`
sets orientation.

---

## appearance.yaml — Layer 3, look

References semantics/geometry by id. Never defines position or size.

```yaml
theme: japandi                    # optional: a theme file provides defaults

room_finishes:
  living:  { floor: wood, walls: warm_white }
  bedroom: { floor: wood, walls: warm_white }

materials:                        # the old SPEC §7 table lives here now, extensible
  wood:       { color: "#d9bd95", texture: oak_plank }
  warm_white: { color: "#f4f0e8", finish: matte }

assignments:                      # furniture id → concrete product or material
  sofa1:        { product: ikea.soderhamn.beige }
  bed1:         { product: ikea.malm.oak_160 }
  coffee_table: { material: wood }   # no product chosen yet — still renders as a box
```

---

## products.yaml — catalog

Plain data, one entry per purchasable product. `kind` must match the
furniture vocabulary; `dims` lets the validator check fit against the
declared footprint (± tolerance); `tags` are what the AI filters on.

```yaml
ikea.soderhamn.beige:
  kind: sofa
  name: "SÖDERHAMN 3-seat sofa"
  dims: [221, 99, 83]             # w × d × h cm
  price: { amount: 2400, currency: PLN }
  url: "https://www.ikea.com/pl/en/p/soderhamn-..."
  tags: [fabric, beige, scandinavian, japandi]

ikea.malm.oak_160:
  kind: bed_double
  name: "MALM bed frame 160×200, oak veneer"
  dims: [176, 209, 100]
  price: { amount: 1049, currency: PLN }
  url: "https://www.ikea.com/pl/en/p/malm-..."
  tags: [wood, oak, minimal, japandi]
```

---

## Cross-layer rules (what the validator enforces)

1. Every id referenced upward must exist below: `semantics.rooms` keys ⊆
   geometry room ids; `assignments` keys ⊆ furniture ids; `product:`
   values ⊆ products.yaml keys.
2. Layers never reach down to redefine: appearance cannot move a sofa,
   semantics cannot move a wall.
3. Product fit: assigned product `dims[0..1]` must be within the declared
   `footprint` ± 5 cm, else a warning ("product is 221 cm, footprint says
   220 — update footprint or pick another product").
4. Missing upper layers are valid — a geometry-only project builds a
   structural plan; geometry+semantics builds a furnished plan with
   placeholder boxes.
5. `kind` values come from one fixed vocabulary shared by semantics and
   products — this is the join key that makes AI product search reliable.
