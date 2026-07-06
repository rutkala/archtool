# archtool — Target Architecture (merged)

This document merges the layered declarative-design architecture (geometry /
semantics / appearance) with the existing archtool implementation
(compiler pipeline, resolved model, backends). Where the two conflicted,
the layered architecture wins. archtool's compiler discipline —
determinism, SPEC as contract, resolved intermediate model, backend
plugins — is kept as the execution engine underneath.

---

## 1. Core idea

**archtool is a deterministic compiler; the layers are its source language.**

A *project* is a directory of layered YAML files. The compiler resolves
them into one canonical model, validates each layer with layer-appropriate
rules, and hands the resolved model to backends. AI never runs inside the
compiler; AI *operates* the compiler through an MCP server and edits the
YAML files directly.

```
project/
  geometry.yaml      # Layer 1 — pure math: outline, points, walls, openings, rooms(shape)
  semantics.yaml     # Layer 2 — meaning: room purposes, zones, furniture placement
  appearance.yaml    # Layer 3 — look: materials, colors, product mapping
  products.yaml      # catalog: real products with dimensions, prices, links
  archtool.yaml      # project config: spec version, units, enabled rulesets
```

Each layer may only reference the layers **below** it (appearance →
semantics → geometry). Geometry knows nothing about kitchens; semantics
knows nothing about oak.

---

## 2. Conflict resolutions (what changes in archtool)

| Topic | Current archtool | Target (priority) |
|---|---|---|
| File layout | Single `dom_dane.yaml` | Split into layered files above. `dom_dane.yaml` becomes `geometry.yaml` (minus appearance fields). |
| `floor: wood` on rooms | In geometry file | Moves to `appearance.yaml` (`room_finishes:`). Room in geometry is shape + id only. |
| Floor→color table (SPEC §7) | In geometry SPEC | Moves to an appearance SPEC section; colors are appearance data, resolvable per theme. |
| Room `purpose` (planned) | Anticipated in geometry model | Lives in `semantics.yaml`, keyed by room id. |
| Compliance rules (SPEC §11) | One future framework | Split by layer: geometric code rules (door widths, room heights) stay; ergonomic/clearance rules become **semantic validation** (need furniture + purpose). |
| AI access | CLI + CLAUDE.md | Add **MCP server** exposing the CLI verbs as tools (see §6). CLI remains the ground truth; MCP is a thin wrapper. |
| Building metadata | Mixed into `building:` | Registry ids, address → `archtool.yaml` project config; `building:` keeps only geometric constants (heights, default thicknesses). |

Everything else in archtool is confirmed: named-point namespace, wall
axis + justify model, opening cut semantics, resolved model as the only
backend input, deterministic output, diagnostics naming the offending
element.

---

## 3. The layers

### Layer 1 — geometry.yaml (exists today, minus appearance)
Walls, openings, rooms as coordinates. Validation: polygon validity,
openings on wall axes, no opening overlaps on a wall, sill+height ≤
ceiling, rooms inside outline, room/wall consistency.

### Layer 2 — semantics.yaml (next major build)
```yaml
rooms:
  living:                 # references room id from geometry.yaml
    purpose: habitable    # habitable / kitchen / bathroom / technical / circulation
    zones:
      - id: tv_zone
        area: [[600,400],[900,700]]
furniture:
  - id: sofa1
    kind: sofa            # abstract kind, not a product
    footprint: [220, 95]  # cm, w × d
    room: living
    place:
      against_wall: w3    # declarative placement primitives
      align: center
      offset: 0
    clearance_front: 90   # walkway the validator must keep free
  - id: dining_table
    kind: table
    footprint: [180, 90]
    room: living
    place:
      at: [750, 520]      # or absolute position
      rotation: 0
```
Placement is declarative (`against_wall`, `align`, `at`, `facing`),
resolved by the compiler into coordinates — the same named-point
philosophy extended to furniture. Semantic validation: no overlaps,
door swings kept clear, minimum walkway widths, clearances per furniture
kind (ergonomic guidelines encoded as a ruleset).

### Layer 3 — appearance.yaml
```yaml
theme: japandi            # optional named theme providing defaults
room_finishes:
  living: { floor: wood, walls: "#f4f0e8" }
materials:
  wood: { color: "#d9bd95", texture: oak_plank }
assignments:
  sofa1:
    product: ikea.soderhamn.beige   # from products.yaml
```
Themes are data: a theme file maps abstract kinds/materials to palettes
and product families, so "switch to industrial" is a one-line change the
AI can make. Appearance validation: every assignment references an
existing furniture id; product footprint fits the declared footprint
(±tolerance); palette contrast/consistency warnings.

### products.yaml — catalog
```yaml
ikea.soderhamn.beige:
  kind: sofa
  dims: [221, 99, 83]     # w × d × h cm
  price: { amount: 2400, currency: PLN }
  url: https://...
  tags: [fabric, beige, scandinavian, japandi]
```
Kept as plain data so the AI can search/filter it; `kind` + `dims` +
`tags` are what make LLM product selection reliable (hard constraints in
data, style judgment in the model).

---

## 4. Pipeline (unchanged shape, more stages)

```
layered YAML ─resolve─▶ ResolvedModel ─validate(L1,L2,L3)─▶ backends
                                                    ├─ svg        plan views: structure / furniture / finishes
                                                    ├─ gltf       3D scene (rooms, walls w/ cuts, furniture boxes→models)
                                                    ├─ blender    photoreal render via headless bpy + Cycles
                                                    ├─ bom        shopping list w/ prices from products.yaml
                                                    └─ json       resolved model dump (AI inspection)
```

- ResolvedModel grows optional sections (`furniture`, `finishes`); every
  backend keeps reading only the ResolvedModel.
- SVG backend gains *views*: `--view structure|furniture|finishes`.
- glTF backend first, Blender renderer second (consumes the same glTF).
- Missing upper layers are fine: geometry-only projects still compile.

---

## 5. Validation = the AI feedback loop

Three rulesets, run per layer, all returning archtool Diagnostics:
1. **geometry** (hard errors) — exists.
2. **ergonomics** (warnings/errors) — clearances, walkways, door-swing
   conflicts, kitchen work triangle. This is what compensates for LLM
   spatial-reasoning weakness: AI proposes, validator disposes.
3. **compliance** (`pl_wt`, opt-in) — legal minimums, as in SPEC §11.

Design rule kept from archtool: every diagnostic names the element and
the fix direction ("Furniture 'sofa1': blocks door 'D2' swing by 34 cm —
move ≥ 34 cm along wall w3").

---

## 6. AI access layer (MCP)

Thin MCP server wrapping the CLI, tools mirror the verbs:
- `read_project`, `write_layer(file, content)` — file access
- `validate(project)` → diagnostics as structured JSON
- `build(project, backend, view)` → output path + (for svg/render) image
  returned for visual inspection
- `resolve(project)` → resolved-model JSON (lets AI *see* computed
  coordinates instead of guessing)
- `search_products(kind, max_dims, tags, budget)` → catalog query

Loop the AI runs: edit YAML → validate → fix diagnostics → build svg →
look → iterate → render. Determinism guarantees the loop converges on
facts, not on model moods.

---

## 7. Build order (merged roadmap)

1. **Layer split** — extract appearance fields from `dom_dane.yaml` into
   `appearance.yaml`; introduce `archtool.yaml`; multi-file resolver. Small,
   mechanical, unlocks everything.
2. **Validator hardening** — opening-overlap check, room/wall consistency.
3. **glTF backend** — walls extruded with opening cuts, room floors;
   view in any glTF viewer / Three.js page.
4. **Semantics layer** — furniture schema + placement resolver +
   ergonomics ruleset + furniture view in SVG.
5. **MCP server** — wrap CLI; start designing interiors with AI for real.
6. **Products + BOM** — catalog, assignments, shopping-list backend.
7. **Blender backend** — headless Cycles renders from the glTF scene.
8. **Themes + AI image variations** — theme files; optional ControlNet
   pass on renders for style exploration.

Steps 1–4 keep the current codebase shape; nothing is thrown away.

---

## 8. Principles (binding)

- Layers only reference downward. Appearance never defines geometry.
- Backends read only the ResolvedModel.
- Same input → same output, byte-stable where possible. No AI, no
  network at build time.
- Diagnostics are the product: precise, named, actionable.
- The AI is a *user* of the tool, never a component of it.
