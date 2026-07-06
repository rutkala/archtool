# VISION.md — why archtool exists, beyond floor plans

This document is background and direction, not a spec. Nothing here changes
the v0.1 scope in CLAUDE.md; it exists so that future feature decisions are
made against the same mental model. The operational contract remains SPEC.md.

## The real product is a method

archtool compiles buildings, but the reason it exists is larger: it is the
first exemplar of a **repeatable method for building AI-operable tools** —
tools whose products can be authored, understood, and safely modified by AI,
in any domain. Master the method on floor plans and interior design, and the
same playbook applies to the next domain, and the next. The transferable
asset is the method as much as the tool.

## Three layers of AI involvement

For any product, AI can participate at three levels, and each level depends
on the one below it:

1. **AI builds the tool.** archtool itself is developed with Claude Code.
2. **AI uses the tool to build products for customers.** An AI authors
   `dom_dane.yaml` from a conversation with a client, then compiles it into
   deliverables. This works only because the tool's input is a plain-text,
   validated, spec-governed format.
3. **AI mediates between the finished product and its users.** A client says
   "make the utility room 30 cm wider"; the AI edits the YAML, revalidates,
   and recompiles. The open problem at this layer is mapping fuzzy human
   intent onto precise declarations — and the rulebook (see below) is what
   makes that safe: after interpreting a vague request, the AI can *check*
   that its interpretation still produces a legal, well-formed building.

## As-code is the enabler

Layers 2 and 3 are only possible when the product's source of truth is
**plain text, declarative, diffable, and governed by a versioned spec**.

The motivating contrast is PowerBI: a `.pbix` file is binary — AI can help
you build the report, but AI cannot live *inside* the artifact. The `.pbir`
format is text — suddenly the artifact itself is AI-operable. dbt (analytics
as code), Terraform (infrastructure as code), and Vega-Lite (charts as
declarative JSON) are the same move in other domains. archtool belongs to
this family: buildings as code.

## Vocabulary, not language

The input format is deliberately **not a programming language**. Like
Vega-Lite, it is a *schema*: a fixed set of domain nouns and constraints on
how they combine — no control flow, no functions, nothing only a programmer
can read.

The guiding principle: **transcribe the domain's existing professional
terminology; never invent terms.** `wall`, `opening`, `sill`,
`load_bearing`, `room` are the words an architect already uses. The grid
axes labeled `1, 2, 3` / `A, B, C` follow a convention that has been on real
construction drawings for a century — archtool codifies it so a machine can
derive and check it. SPEC.md is the dictionary for this vocabulary; reading
it is how any tool or model (or person) learns to speak it.

## The rules-first playbook

The repeatable method for opening a new domain:

```
domain rulebook  →  required nouns  →  schema  →  validator  →  tool
```

Start by collecting the domain's codified rules (building codes, design
guidelines, ergonomic standards). The rules dictate what the vocabulary must
be able to express: a door-width rule can only exist if door widths are
declarable; a "habitable room ≥ 16 m²" rule requires rooms to have a
declarable purpose. Work backward from the rules to the nouns, formalize the
nouns as a schema, enforce the schema with a validator, and only then build
the compiler and its backends. SPEC.md §11 (the `pl_wt` ruleset) is the live
example of this ordering inside archtool.

## Principles borrowed from the ecosystem

Microsoft's Fabric Apps / Rayfin (announced at Build, June 2026) ships the
same thesis — declarations in, generated product out, explicitly marketed
for "developers or the coding agents working on their behalf". Three of its
practices are adopted here, and one is deliberately rejected:

- **One-way sync.** In Fabric Apps the deployed database is read-only in the
  portal; schema changes must come from the declaration or the app breaks.
  archtool's version: **outputs are never a writable surface.** The YAML is
  the only place truth lives; every SVG (and future DXF/glTF/BOM) is
  regenerable and never hand-edited.
- **Policies declared next to the thing they govern.** Rayfin's `@role`
  decorators sit on the entity they protect. When §11 compliance is
  implemented, rules should likewise attach declaratively to the element
  types they constrain, rather than living in a separate engine config.
- **The validator is the type system.** Rayfin gets instant validation from
  the TypeScript compiler; archtool gets it from pydantic + shapely via
  `archtool validate`. Consequence: **error-message quality is architecture,
  not polish.** For a human a good error is UX; for an agent in a
  write → validate → fix loop, it is the feedback signal that makes the loop
  converge. This is why "good errors are a primary goal" in CLAUDE.md.
- **Not borrowed: a programming language as the declaration format.** Rayfin
  declares data models in TypeScript — powerful for developers, but it makes
  the artifact legible only to programmers. archtool stays with YAML plus a
  strong validator, keeping the artifact readable by the domain expert who
  owns it.

References:
[Fabric Apps overview (Microsoft Learn)](https://learn.microsoft.com/en-us/fabric/apps/overview) ·
[Rayfin announcement (SiliconANGLE)](https://siliconangle.com/2026/06/02/microsoft-launches-rayfin-let-developers-agents-build-app-backends-fabric/)
