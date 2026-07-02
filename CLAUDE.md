# archtool — project brief for Claude Code

## What this project is

`archtool` is a **compiler for buildings**: a command-line tool that turns a
declarative specification of a building (plain-text YAML) into a full package of
architecture and interior-design deliverables. Think **"dbt, but for buildings"** —
architecture-as-code and design-as-code.

The user authors a building in YAML, runs a CLI command, and gets deterministic
outputs: floor plans, 3D models, interior layouts, renders, technical drawings,
and a bill of materials. **No AI is involved at build time.** Compilation is
pure, mechanical, and repeatable.

### Critical framing: the product is the TOOL, not any one building

The repository contains an example building (`examples/example_house/dom_dane.yaml`)
based on a real house. **That file is only a test fixture** — something to exercise
the compiler against. Do not optimise for that specific house. Every feature must
generalise to *any* building expressed in the format. If a choice would only work
for the example, it is wrong.

## Current phase: v0.1 — build ONLY this

- Parse + resolve `examples/`.
- Validate (schema + geometry; see "Validation").
- **One output backend: SVG** (a 2D floor plan). No HTML. No 3D yet.
- A CLI with two commands:
  - `archtool validate` — schema + geometry checks; precise errors; non-zero exit on failure.
  - `archtool build` — validate, then render the SVG floor plan.
- Optional if quick: `archtool build --watch` to re-render on file save.

**Out of scope for v0.1** (leave clean extension points, do NOT implement):
HTML, 3D/glTF, DXF, IFC, construction detail, interior furniture, catalogs, BOM,
rendering, compliance rules. The architecture must *anticipate* these; v0.1 must
not *contain* them.

## Architecture (do not deviate without discussion)

Three strictly separated stages — this is what guarantees "same source, multiple
consistent outputs":

1. **Parser / resolver** — load YAML, validate schema, resolve *named points*
   into coordinates, produce one canonical in-memory model.
2. **Resolved intermediate model** — a plain, canonical data structure
   (serialisable to JSON). **Every backend reads THIS, never the raw YAML.**
3. **Backends (plugins)** — each takes the resolved model and writes one output
   format. Adding an output = adding a backend, touching nothing else.

```
dom_dane.yaml ──parse/resolve──▶ resolved model (JSON) ──backend──▶ output
                                                        ├─ svg        (v0.1)
                                                        └─ dxf, gltf, bom, ... (future)
```

## Core principle: determinism

The same input YAML must always produce the same output, byte-for-byte where
possible. No randomness, no AI calls, no network at build time. If two runs
differ, that's a bug. This is the entire point of the tool.

## The spec

`SPEC.md` (repo root) is the authoritative, versioned contract for how the YAML
is interpreted — coordinate system, wall axes, openings, materials→colours, and
the formal-rules framework. Implement validation and backends to follow @SPEC.md
exactly. If SPEC.md is ambiguous, ask rather than guess. The YAML declares which
spec version it targets via `building.format_version`.

## Validation (the heart of correctness)

Run by `archtool validate`, two layers:

1. **Schema** — `pydantic`. Reject malformed files (missing/extra fields, wrong
   types) with messages naming the field.
2. **Geometry** — `shapely`. Implement SPEC.md geometry checks: every point name
   resolves; outline and rooms are valid closed polygons; openings lie on a wall
   axis within its span; sill+height ≤ ceiling; rooms inside the outline; room
   areas sum to less than the outline.

A later layer (NOT in v0.1, but the framework should anticipate it):

3. **Compliance** — validate against formal building codes / design standards
   (see SPEC.md §11). This produces warnings/errors like "bedroom below minimum area".

**Error messages must name the offending element and reason**, e.g.
`Room 'kitchen': point 'P21' not found in points (did you mean 'P12'?)`.
Good errors are a primary goal.

## Tech choices

- Python 3.11+ (3.14 is installed).
- `pydantic` (schema), `shapely` (geometry), `typer` (CLI), SVG output
  (hand-written or `svgwrite`), `watchdog` (optional watch mode).
- Installable package (`pip install -e .`) with `pyproject.toml` and an
  `archtool` console entry point.
- Use a virtual environment (`.venv`).

## Working style

- Build in small, reviewable stages. Suggested order: project skeleton +
  `pyproject.toml` → pydantic models → resolver → validator + `validate` →
  SVG backend + `build`.
- After each working stage, STOP so changes can be reviewed and committed.
- Write tests for the validator against the example fixture.
- Prefer clear, boring, deterministic code over cleverness.
- Everything in English — code, comments, docs, and YAML field names.