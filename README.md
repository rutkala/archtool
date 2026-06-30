# archtool

A compiler for buildings: turns a declarative YAML building specification
into architecture and interior-design deliverables. v0.1 parses, validates,
and renders an SVG floor plan.

See `CLAUDE.md` for project scope and `SPEC.md` for the YAML format
contract.

## Install

```
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## Usage

```
archtool init myhouse                  # scaffold a new project in ./myhouse/
archtool validate myhouse/dom_dane.yaml
archtool build myhouse/dom_dane.yaml
archtool build myhouse/dom_dane.yaml --watch
```
