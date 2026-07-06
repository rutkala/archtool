# archtool — Decision Log (ADR)

Each entry: what was decided, why, and which documents it changes.
Status: accepted unless marked otherwise. New decisions append; reversals
get a new entry superseding the old one (never edit history).

---

**D01 — Layered declarative core.** Design data lives in layered text
files: geometry → semantics → appearance (+ product catalog). Layers
reference only downward. *Why:* independent change of look vs meaning vs
shape; well-scoped AI tasks per layer. → target-architecture.

**D02 — Compiler discipline.** Deterministic compile from YAML to a
resolved model; backends read only the resolved model; no AI or network
at build time. AI operates the tool (via CLI/MCP), never runs inside it.
*Why:* repeatable feedback loop; trust. → target-architecture.

**D03 — Intent over coordinates.** Positions by relation (grid refs,
anchors, host+offset openings, seed-claimed derived rooms); raw [x, y]
is the escape hatch. *Why:* one number per fact; whole error classes
removed by construction. → language reference (v2 draft).

**D04 — Docs are the contract (Vega-Lite model).** JSON Schema generated
from models; SPEC for semantics; reference doc; example gallery compiled
in CI; compact language card. Doc examples that break fail the build.
*Why:* docs cannot drift from implementation. → docs plan.

**D05 — No AI ceiling on the language.** The language is designed as the
best language for describing buildings; AI-friendliness follows from
good design (compositional grammar, formal schema, determinism), never
from limiting expressiveness. → language reference, preamble.

**D06 — Corpus-driven language development.** Real buildings are
authored in the draft syntax before implementation; friction findings
drive versioned draft revisions; corpus files become golden tests.
*Why:* language bugs are cheapest before code exists. → process.

**D07 — Pipeline extends upward: sketch → brief → drawing.** Above
geometry sit two optional stages: freehand sketches (informal artifacts,
e.g. photos, stored in the project) and a structured sketch `brief.yaml`
(rooms, ~areas, adjacencies, orientations — the architectural program).
*Why:* the sketch/drafting distinction; intent captured before geometry.
→ target-architecture, new brief format spec.

**D08 — Ladder, not procedure.** Any stage is a valid entry point; lower
stages are optional context. Whatever stages exist must each be
sufficient to continue from. *Why:* interior-designer scenario — a
client's DWG arrives with no brief and no sketch. → target-architecture.

**D09 — Shared artifacts, human-first, always both.** Every artifact is
authorable and readable by both humans and AI; human ergonomics wins
format decisions; AI adapts. No stage may depend on remembered
conversation — roles communicate only through artifacts. *Why:* archtool
must work human-only; prevents spec rot when one mind wears many hats.
→ target-architecture, principles.

**D10 — Importers produce drafts, never truth.** Foreign inputs (JPG,
PDF, DXF; DWG via DXF conversion; later IFC) are front-ends that emit
candidate files in the same language, marked unverified, promoted by
review. Core language stays small; importers/exporters multiply around
it (IR pattern). → target-architecture.

**D11 — Checks vs reviews.** Two enforcement kinds in the chain of
promises: *checks* — computable, run by the compiler, block or pass
(geometry vs brief: areas, adjacency); *reviews* — interpretive,
performed by human or AI, produce non-blocking observations (brief vs
freehand sketch). The brief format is designed for maximum checkability
(tolerances as data, e.g. area: ~12 ±15%). → target-architecture,
brief spec, validator design.

**D12 — Corpus findings pending for language draft.2** (from corpus
entry #1, Gruszowa 60): (a) T-junctions expressible by an endpoint lying
exactly on another wall's axis, not only by anchor form; (b) new
informational diagnostic W04 "free-standing wall end"; (c) conversion
surfaced a source-data discrepancy (D1 width 200 vs commented 185) —
resolve against the real building. → language reference draft.2.

**D13 — Docs need an authoring-workflow tutorial** (friction log #1):
how to approach a blank file (grid → shell + load-bearing → partitions →
openings → rooms, the professional order) plus a short "how architects
think" primer linking curated external resources. Reference ≠ tutorial;
both are required (Vega-Lite ships both). → docs plan.

**D14 — Landscape survey: niche confirmed open; adopt, don't rebuild,
at the edges.** Survey of the CAD-as-code ecosystem (cadascode.com /
Polyglot, Zoo KCL + Zookeeper, CadQuery/Build123d/OpenSCAD, Hypar
Elements, AI floor-plan generators) found no declarative, human+AI
authorable building-description language — text-first tools are
mechanical CAD and imperative; the closest AEC neighbor (Hypar Elements)
is a C# code library, not a data language; AI floor-plan projects emit
images without an editable representation. Independent convergence of
three efforts on text-first/git-native/deterministic validates D02–D05.
Consequences: (a) adopt `ezdxf` for DXF import; (b) reference Hypar's
Elements schema for element typing and as a possible IFC/JSON export
target; (c) study Zoo's documentation architecture (Book / Reference /
Stdlib / interactive samples gallery) as the production-proven form of
our D04 docs plan, including rendered examples beside source; (d) track
Zoo's Zookeeper as prior art for the MCP agent loop. → docs plan,
importer roadmap, backend roadmap.

**D15 — Step-1 language conventions resolved.** (a) Y-axis grows **up**
(north-up, map/architect convention); screen flipping is the SVG
backend's job, not the author's (per D09, human ergonomics wins). (b)
Grid refs: terse concatenation (`2A`) by default; dot separator
(`8a.D`) allowed always and **required** when labels make a ref
ambiguous — the compiler identifies such cases. (c) Opening `at` accepts:
number (offset from host start), `center`, and negative numbers
(offset from host end). *Consequence:* corpus #1 re-authored Y-up;
language reference → draft.2 together with D12 findings.

**D16 — Brief format: minimal checkable set.** Per room: `purpose`,
`area: ~12` (`~` = ±15% default; `{min, max}` explicit form),
`adjacent_to: [ids]`, `windows_facing: [directions]`, `count` for
repeated rooms. Global: total area, storeys. Everything in the format is
compiler-checkable against geometry (D11); visual intent stays in
freehand sketches, enforced by review not check. → brief spec (new
one-page doc).

**D17 — Promotion via file-local status field.** Every layer file
carries `status: draft | reviewed`. Importers always emit `draft`;
`validate` warns on draft files; promotion = editing the field after
review, making every promotion an attributable git change. No registries
or sidecar files. → language reference draft.2, importer spec.

---

## Open questions

None — all resolved as of D15–D17. New questions enter here as they
arise from corpus work and evaluation sessions.
