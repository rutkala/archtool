"""Output backends. Each backend takes a `ResolvedModel` and writes one
output format, per CLAUDE.md: "Adding an output = adding a backend,
touching nothing else."
"""

from .svg import write_svg

# Registry of available backends, keyed by name. v0.1 ships only "svg";
# future backends (dxf, gltf, bom, ...) register here without touching
# the resolver, validator, or any existing backend.
BACKENDS = {
    "svg": write_svg,
}

__all__ = ["BACKENDS", "write_svg"]
