# HANDOFF — archtool v2 language work

Read this first. This package continues the archtool project (repo:
rutkala/archtool) after a design phase that produced a v2 language
design. Everything agreed lives in these files; nothing depends on any
prior conversation. **docs/DECISIONS.md is the master artifact** — 17
accepted decisions (D01–D17) govern all work; read it in full before
changing anything.

## What archtool is (one paragraph)

A deterministic "compiler for buildings": layered declarative YAML
(brief → geometry → semantics → appearance, plus a product catalog) is
resolved into a canonical model, validated, and rendered by backends
(SVG plans, glTF, Blender renders, BOM). AI operates the tool via
CLI/MCP but never runs inside the compiler (D02). Every artifact is
human-first and authorable by both humans and AI (D09). The existing
repo implements a v1 point-based format with an SVG backend and 43
passing tests; v2 (this package) is a redesign of the *language*, not
of the compiler discipline — resolver/backends architecture carries
over.

## Artifact map

| File | Status |
|---|---|
| docs/DECISIONS.md | authoritative, current |
| docs/language/reference.md | **draft.1 — owes draft.2** (see queue) |
| docs/language/language-card.md | draft.1, condensed companion to reference |
| docs/language/design-rationale.md | why v2 departs from v1 (background) |
| docs/language/layers-by-example.md | semantics/appearance/products layers by example; geometry section partially superseded by D15 |
| docs/architecture/target-architecture.md | **owes revision** per D07–D11 (brief layer, ladder entry, importers, checks-vs-reviews) |
| docs/architecture/system-diagram.mermaid | early pipeline sketch, superseded in details by target-architecture + D07–D11 |
| corpus/01_gruszowa60/geometry.yaml | corpus entry #1 in draft.1 conventions — **owes re-authoring** per D15 (Y-up) |

On conflicts: DECISIONS.md wins over every other document; newer D-numbers
win over older text anywhere.

## Work queue (in dependency order)

1. **Language reference draft.2.** Fold in: D15 (Y-axis grows UP; grid
   dot-separator rule; opening `at` accepts number / `center` /
   negative-from-end), D17 (`status: draft|reviewed` field on every
   layer file), D12 (T-junction expressible by endpoint lying exactly on
   another wall's axis; new W04 "free-standing wall end" informational
   diagnostic). Bump the version header; add a revision-history section.
2. **Re-author corpus #1** (corpus/01_gruszowa60/geometry.yaml) in
   draft.2 conventions — Y-up flips all y values; keep ids and comments.
3. **Brief format spec** — new one-page doc per D16 (purpose, area with
   `~`=±15% tolerance, adjacent_to, windows_facing, count; global total
   area + storeys; everything compiler-checkable). Then write
   corpus/01_gruszowa60/brief.yaml as its first example.
4. **Target-architecture revision** per D07–D11.
5. **Corpus entries #2–#5** (a boring rectangular apartment; an L-shaped
   bungalow; something with a diagonal or irregularity; a two-partition
   studio) — per D06, authored BEFORE implementation; each friction
   finding becomes a decision-log entry and possibly draft.3.
6. **Implementation**, only after the corpus writes cleanly: v2 resolver
   (positions → grid/anchors; region polygonization for derived rooms
   via Shapely), validator rules E01–E11/W01–W04, SVG backend for v2,
   `archtool migrate` (v1 → v2, per design-rationale.md §Migration),
   corpus files become golden tests.

## Working rules (binding, from the decision log)

- Docs are the contract (D04): change reference/spec first, code second;
  every doc example must compile in CI once a compiler exists; every
  E/W diagnostic maps to one test.
- Decision-log discipline: significant design choices get a new D-entry
  (append-only, with rationale and affected docs) BEFORE implementation.
- Determinism (D02): same input → same output; no AI, no network in the
  build path.
- Corpus-first (D06): language changes are validated by re-authoring the
  corpus, not by intuition.
- Layers reference only downward (D01); importers emit `status: draft`,
  never truth (D10, D17).

## Repo integration notes

- Place `docs/` and `corpus/` at repo root alongside the existing v1
  code; do not delete v1 — it stays as the migration source and its SPEC
  remains valid for format_version 1.x files.
- Update CLAUDE.md to point at docs/DECISIONS.md and
  docs/language/reference.md as the governing documents for v2 work.
- Suggested first session prompt: "Read docs/HANDOFF.md and
  docs/DECISIONS.md, then execute work-queue item 1 (language reference
  draft.2) and show me the diff of the reference before committing."
