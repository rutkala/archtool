# Proposal: archtool geometry language v2 (designed from scratch)

Design goal: the file should read like a *description of a building*, not
like a list of coordinates. A human or an AI should be able to say "make
the entrance 10 cm wider" by changing **one number**. Every redundancy in
the format is a future inconsistency, so the language has exactly one
source of truth for each fact and derives everything else.

Five principles drove every choice below:

1. **Intent over coordinates.** Positions are expressed relative to
   things (grid lines, walls, other elements) wherever possible; raw
   `[x, y]` is the escape hatch, not the default.
2. **Single source of truth.** Walls define space; rooms are *derived*
   enclosed regions that you label — never traced a second time.
3. **One number per fact.** An opening is a place + a width, not two
   endpoint coordinates that must be kept consistent by hand.
4. **Structure anticipates reality.** Levels (storeys) exist from day
   one; the exterior shell is distinct from interior walls.
5. **cm, integers, Y-down.** (Confirmed from the current design — these
   were the right calls.)

---

## geometry.yaml — full example (fresh house, single level)

```yaml
building:
  name: "Proposal demo house"
  format_version: "2.0"

grid:                     # the architectural reference grid, defined ONCE
  x: { "1": 0, "2": 350, "3": 650, "4": 1050 }     # vertical lines (x=…)
  y: { "A": 0, "B": 420, "C": 700 }                # horizontal lines (y=…)

levels:
  - id: ground
    floor_z: 0
    ceiling_height: 280

defaults:
  exterior_wall: { thickness: 30 }
  partition:     { thickness: 12 }
  door:          { width: 90, height: 205, sill: 0 }
  window:        { width: 120, height: 150, sill: 90 }

# ---- SHELL: the exterior envelope, one closed loop per level ----------
# Corners are grid references ("1A" = intersection of x-line 1, y-line A)
# or raw [x, y]. The loop auto-closes. Each edge gets an automatic id
# from its corners: shell.1A-4A, shell.4A-4C, ... (direction as written).

shell:
  ground:
    outline: [1A, 4A, 4C, 1C]
    wall: exterior_wall            # profile from defaults

# ---- WALLS: interior walls define ALL interior space ------------------
# Endpoints: grid refs, raw [x,y], or anchors on other elements.
# "on:" projects a point onto an existing wall/shell edge at an offset.

walls:
  - id: w_bedroom
    level: ground
    from: 2A                        # grid intersection
    to:   { on: shell.1C-1A, at: 350 }   # hits west shell edge 350cm from corner 1C
    type: partition

  - id: w_bath
    level: ground
    from: 3A
    to:   { on: w_bedroom, at: 300 }     # T-junction: 300cm along w_bedroom
    type: partition

# ---- OPENINGS: a host + a position + a size. Never two endpoints. -----
# "at" = offset of the opening's start along the host, measured from the
# host's `from` end. Width/height/sill come from defaults unless set.

openings:
  - id: entrance
    in: shell.1A-4A                # host: a shell edge or wall id
    at: 480
    type: door
    width: 100                     # overrides the default 90
    hinge: start                   # which jamb carries the hinge
    swing: in                      # in|out — drawn and clearance-checked

  - id: win_living
    in: shell.4A-4C
    at: 90
    type: window
    width: 180

  - id: win_bedroom
    in: shell.1A-4A
    at: 60
    type: window

  - id: d_bedroom
    in: w_bedroom
    at: 210
    type: door
    hinge: end
    swing: in

  - id: d_bath
    in: w_bath
    at: 40
    type: door
    width: 80

# ---- ROOMS: labels on derived regions, not geometry -------------------
# The compiler computes enclosed regions from shell + walls. A room is
# claimed by ONE interior seed point. Unlabeled regions are legal and
# reported (as info) by the validator. Room polygons, areas, and
# perimeters are OUTPUTS, visible via `archtool resolve`.

rooms:
  - id: living
    name: "Living room"
    seed: 3B                       # grid ref or [x, y] anywhere inside
  - id: bedroom
    name: "Bedroom"
    seed: [170, 200]
  - id: bath
    name: "Bathroom"
    seed: [500, 200]
```

---

## Why each departure from the current format

### 1. Grid first, points second
Current: axis labels are annotations attached to outline points; every
location is a named point in a flat namespace you must invent ids for
(`oUW1`, `d3E3`…). Proposal: the grid is declared once as the coordinate
vocabulary, and most positions are written as grid refs (`2A`) or offsets.
The point-name bookkeeping — the most tedious, most error-prone part of
authoring, for humans and LLMs alike — disappears. Raw `[x, y]` remains
valid anywhere a position is expected.

### 2. Openings = host + offset + width
Current: an opening is two absolute endpoint coordinates, which (a) must
be computed by hand, (b) can silently disagree with the wall axis — a
whole validator rule exists just to catch that, and (c) make "widen this
door" a two-coordinate edit. Proposal: `in: + at: + width:` cannot be
off-axis *by construction*; the failure mode is deleted from the language
instead of detected. Widths come from `defaults:` so a typical door is
two lines.

### 3. Rooms are derived, not drawn
Current: room outlines are hand-traced point lists that duplicate what
the walls already imply — the two can disagree and nothing catches it.
Proposal: the compiler computes enclosed regions (Shapely: polygonize the
wall/shell axes) and a room is just a **seed point + a name** claiming
one region. Move a wall and every affected room updates; disagreement is
impossible. Net floor areas (inside wall faces, not axes) come out of the
same computation — more accurate than the current axis-polygon shoelace.

### 4. Shell vs walls, levels from day one
Current: exterior is implied by `outline:`, one implicit storey.
Proposal: `shell:` is explicit and per-level, every element carries a
`level:`, and vertical structure (stairs, multi-storey) has a home when
it arrives — retrofitting levels later would touch every file.

### 5. Doors know their hinge and swing
Current: the swing arc is a drawing convention (hinged at `from`).
Proposal: `hinge:` and `swing:` are data — the ergonomics validator needs
them (door-swing clearance), and "flip this door" becomes a one-word edit.

### 6. defaults: block
Typical elements should be near-zero-config; a standard window is
`{ in: …, at: …, type: window }`. LLMs writing the format make fewer
errors when the common case has the fewest degrees of freedom.

---

## What survives from the current design (kept on merit)

cm units · Y-down screen convention · wall axis + thickness + justify
model · opening cut semantics (sill/height through full thickness) ·
strict schema (unknown field = error) · determinism · resolved-model /
backend split · diagnostics naming the element. The `justify:` mechanism
carries over unchanged onto both walls and shell edges.

## Migration note

The current point-based format maps mechanically onto this one (points →
grid refs or raw coords; opening endpoints → host + offset + width; room
outlines → seed points). A `archtool migrate` command can do 95% of it
automatically — worth building as the first test of the new resolver.

## Semantics / appearance layers

Unchanged from the layered proposal already delivered: furniture uses the
same relational placement grammar (`against:`, `in_front_of:`, `at:`),
which is this same design language — position by relation, size by one
number — applied one layer up.
