"""Token schema for lookbook: presets, validation, read/write.

Python 3 stdlib only. No server, no UI concerns in this module -- pick.py is the
only thing that imports it, and the CLI contract in the spec is what callers see.
"""

from __future__ import annotations

import datetime
import json
import os
import re
from typing import Any

SCHEMA_VERSION = 1

CONFIG_RELPATH = os.path.join(".claude", "branding.json")
REFS_RELDIR = os.path.join(".claude", "branding", "refs")

HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

# --------------------------------------------------------------------------
# Presets
#
# Concrete values only. Adjectives do nothing on the next turn -- the calling
# skill needs hexes, families, weights and a spacing base it can paste.
# Keep in sync with references/presets.md.
# --------------------------------------------------------------------------

PRESETS: dict[str, dict[str, Any]] = {
    "editorial-warm": {
        "label": "Editorial Warm",
        "blurb": "Serif display, cream ground, one warm accent, near-zero radius.",
        "tokens": {
            "color": {
                "bg": "#FBF3EF",
                "surface": "#FFFFFF",
                "text": "#1C1512",
                "muted": "#7A6A62",
                "accent": "#C2603F",
                "border": "#E8DBD3",
            },
            "type": {
                "display": {"family": "Fraunces", "weights": [600, 900]},
                "body": {"family": "Source Sans 3", "weights": [400, 600]},
                "scale": [12, 14, 16, 20, 28, 44, 72],
            },
            "radius": {"sm": "2px", "md": "4px", "lg": "8px"},
            "spacing": {"base": 8},
            "shadow": "none",
        },
        "avoid": [
            "Inter, Roboto, DM Sans",
            "em dashes in headings or body copy",
            "indigo/violet gradients",
            "glassmorphism and blur panels",
            "three equal-weight icon+heading+sentence cards",
            "gradient text",
            "pill-shaped buttons -- radius stays under 8px here",
            "pure #FFFFFF page background; the ground is cream",
        ],
    },
    "swiss-neutral": {
        "label": "Swiss Neutral",
        "blurb": "Grotesk, white and black, one accent, visible grid, generous whitespace.",
        "tokens": {
            "color": {
                "bg": "#FFFFFF",
                "surface": "#F4F4F4",
                "text": "#0A0A0A",
                "muted": "#6E6E6E",
                "accent": "#D62828",
                "border": "#111111",
            },
            "type": {
                "display": {"family": "Archivo", "weights": [500, 700]},
                "body": {"family": "IBM Plex Sans", "weights": [400, 600]},
                "scale": [12, 14, 16, 18, 24, 36, 64],
            },
            "radius": {"sm": "0px", "md": "0px", "lg": "0px"},
            "spacing": {"base": 8},
            "shadow": "none",
        },
        "avoid": [
            "Inter, Roboto, DM Sans",
            "em dashes in headings or body copy",
            "indigo/violet gradients",
            "any border-radius -- corners are square",
            "drop shadows and elevation layers",
            "centred hero text; this grid is left-aligned",
            "more than one accent colour",
        ],
    },
    "brutalist": {
        "label": "Brutalist",
        "blurb": "Weight extremes (200 vs 900), hard edges, one loud colour, no shadow.",
        "tokens": {
            "color": {
                "bg": "#F2F0E6",
                "surface": "#FFFFFF",
                "text": "#000000",
                "muted": "#4A4A45",
                "accent": "#FF3B00",
                "border": "#000000",
            },
            "type": {
                "display": {"family": "Space Grotesk", "weights": [300, 700]},
                "body": {"family": "Space Mono", "weights": [400, 700]},
                "scale": [12, 14, 16, 20, 32, 56, 96],
            },
            "radius": {"sm": "0px", "md": "0px", "lg": "0px"},
            "spacing": {"base": 8},
            "shadow": "none",
        },
        "avoid": [
            "Inter, Roboto, DM Sans",
            "em dashes in headings or body copy",
            "indigo/violet gradients",
            "soft shadows, blur, glassmorphism",
            "mid-weight type -- use 300 or 700, nothing between",
            "rounded corners",
            "muted pastel accents",
        ],
    },
    "dark-luxe": {
        "label": "Dark Luxe",
        "blurb": "Near-black ground, thin type, image-led, minimal chrome.",
        "tokens": {
            "color": {
                "bg": "#0B0B0C",
                "surface": "#141416",
                "text": "#EDEAE4",
                "muted": "#8C877E",
                "accent": "#C8A45C",
                "border": "#26252A",
            },
            "type": {
                "display": {"family": "Cormorant Garamond", "weights": [300, 500]},
                "body": {"family": "Jost", "weights": [300, 500]},
                "scale": [12, 14, 16, 20, 30, 48, 80],
            },
            "radius": {"sm": "0px", "md": "2px", "lg": "4px"},
            "spacing": {"base": 8},
            "shadow": "none",
        },
        "avoid": [
            "Inter, Roboto, DM Sans",
            "em dashes in headings or body copy",
            "indigo/violet gradients",
            "neon or saturated accents; the accent is a muted metallic",
            "bold weights above 500",
            "card grids with borders on every side",
            "glow effects",
        ],
    },
    "product-dense": {
        "label": "Product Dense",
        "blurb": "Muted low-saturation, tight radii, high information density, full state coverage.",
        "tokens": {
            "color": {
                "bg": "#FAFAF9",
                "surface": "#FFFFFF",
                "text": "#18181B",
                "muted": "#71717A",
                "accent": "#2F6F5E",
                "border": "#E4E4E7",
            },
            "type": {
                "display": {"family": "Public Sans", "weights": [600, 700]},
                "body": {"family": "Public Sans", "weights": [400, 500]},
                "scale": [11, 12, 13, 14, 16, 20, 28],
            },
            "radius": {"sm": "2px", "md": "4px", "lg": "6px"},
            "spacing": {"base": 4},
            "shadow": "0 1px 2px rgba(24,24,27,0.06)",
        },
        "avoid": [
            "Inter, Roboto, DM Sans",
            "em dashes in headings or body copy",
            "indigo/violet gradients",
            "marketing-scale type; body text stays at 13-14px",
            "decorative hero sections",
            "tables without loading, empty and error states",
            "spacing above 24px between related controls",
        ],
    },
    "custom": {
        "label": "Custom",
        "blurb": "Your own palette, fonts and reference images.",
        # Starting point only -- the UI overwrites every field the human touches.
        "tokens": {
            "color": {
                "bg": "#FFFFFF",
                "surface": "#F6F6F6",
                "text": "#111111",
                "muted": "#6B6B6B",
                "accent": "#C15F3C",
                "border": "#E2E2E2",
            },
            "type": {
                "display": {"family": "Space Grotesk", "weights": [500, 700]},
                "body": {"family": "IBM Plex Sans", "weights": [400, 600]},
                "scale": [12, 14, 16, 20, 28, 44, 72],
            },
            "radius": {"sm": "2px", "md": "4px", "lg": "8px"},
            "spacing": {"base": 8},
            "shadow": "none",
        },
        "avoid": [
            "Inter, Roboto, DM Sans",
            "em dashes in headings or body copy",
            "indigo/violet gradients",
            "glassmorphism and blur panels",
            "three equal-weight icon+heading+sentence cards",
            "gradient text",
        ],
    },
}

PRESET_NAMES = list(PRESETS.keys())

# Order matters: these are written to disk and read back by other skills.
REQUIRED_COLORS = ("bg", "surface", "text", "muted", "accent", "border")
REQUIRED_RADII = ("sm", "md", "lg")


class SchemaError(ValueError):
    """Raised when a config cannot be validated or built."""


# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------


def config_path(project: str) -> str:
    return os.path.join(os.path.abspath(project), CONFIG_RELPATH)


def refs_dir(project: str) -> str:
    return os.path.join(os.path.abspath(project), REFS_RELDIR)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def normalize_hex(value: Any, field: str = "color") -> str:
    if not isinstance(value, str):
        raise SchemaError(f"{field}: expected a hex string, got {type(value).__name__}")
    v = value.strip()
    if not v.startswith("#"):
        v = "#" + v
    if not HEX_RE.match(v):
        raise SchemaError(f"{field}: {value!r} is not a #RGB or #RRGGBB hex colour")
    if len(v) == 4:  # #abc -> #aabbcc
        v = "#" + "".join(c * 2 for c in v[1:])
    return v.upper()


def _utcnow() -> str:
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _deep_copy(obj: Any) -> Any:
    return json.loads(json.dumps(obj))


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------


def build_config(
    preset: str,
    accent: str | None = None,
    tokens_override: dict[str, Any] | None = None,
    avoid_extra: list[str] | None = None,
    references: list[dict[str, str]] | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Compose a full config document from a preset plus optional overrides."""
    if preset not in PRESETS:
        raise SchemaError(
            f"unknown preset {preset!r}; expected one of {', '.join(PRESET_NAMES)}"
        )

    base = _deep_copy(PRESETS[preset])
    tokens = base["tokens"]
    avoid = list(base["avoid"])

    if tokens_override:
        tokens = _merge_tokens(tokens, tokens_override)

    if accent:
        tokens["color"]["accent"] = normalize_hex(accent, "tokens.color.accent")

    # The avoid list is generated relative to the picked palette: forbid the
    # default nobody chose, not a colour family someone might deliberately want.
    avoid = _tune_avoid(avoid, tokens)

    if avoid_extra:
        for item in avoid_extra:
            if isinstance(item, str) and item.strip() and item.strip() not in avoid:
                avoid.append(item.strip())

    doc: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "preset": preset,
        "tokens": tokens,
        "avoid": avoid,
        "references": references or [],
        "meta": {"createdAt": _utcnow(), "tool": "lookbook"},
    }
    if notes:
        doc["notes"] = notes.strip()

    return validate(doc)


def _merge_tokens(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Shallow-per-group merge. Only known groups survive."""
    out = _deep_copy(base)
    for group in ("color", "radius", "spacing"):
        if isinstance(override.get(group), dict):
            out[group].update(override[group])
    if isinstance(override.get("type"), dict):
        t = override["type"]
        for role in ("display", "body"):
            if isinstance(t.get(role), dict):
                out["type"][role].update(t[role])
        if isinstance(t.get("scale"), list):
            out["type"]["scale"] = t["scale"]
    if "shadow" in override and isinstance(override["shadow"], str):
        out["shadow"] = override["shadow"]
    return out


def _tune_avoid(avoid: list[str], tokens: dict[str, Any]) -> list[str]:
    """Drop avoid-entries that contradict the chosen palette, add the accent lock."""
    accent = tokens["color"]["accent"].upper()
    out = []
    for item in avoid:
        low = item.lower()
        # Never forbid a hue the human deliberately picked.
        if "indigo/violet" in low and _is_violet(accent):
            continue
        if "rounded corners" in low and _max_radius_px(tokens) >= 8:
            continue
        out.append(item)

    lock = (
        f"substituting a different accent; the accent is exactly {accent} "
        "and nothing else"
    )
    if lock not in out:
        out.append(lock)
    return out


def _is_violet(hex_color: str) -> bool:
    r, g, b = _rgb(hex_color)
    mx, mn = max(r, g, b), min(r, g, b)
    if mx == mn:
        return False
    h = _hue(r, g, b)
    sat = (mx - mn) / mx if mx else 0
    return 240 <= h <= 300 and sat > 0.25


def _rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hue(r: int, g: int, b: int) -> float:
    r_, g_, b_ = r / 255, g / 255, b / 255
    mx, mn = max(r_, g_, b_), min(r_, g_, b_)
    d = mx - mn
    if d == 0:
        return 0.0
    if mx == r_:
        h = ((g_ - b_) / d) % 6
    elif mx == g_:
        h = (b_ - r_) / d + 2
    else:
        h = (r_ - g_) / d + 4
    return h * 60


def _max_radius_px(tokens: dict[str, Any]) -> float:
    vals = []
    for key in REQUIRED_RADII:
        raw = str(tokens.get("radius", {}).get(key, "0px"))
        m = re.match(r"^(\d+(?:\.\d+)?)", raw)
        vals.append(float(m.group(1)) if m else 0.0)
    return max(vals) if vals else 0.0


# --------------------------------------------------------------------------
# Validate
# --------------------------------------------------------------------------


def validate(doc: Any) -> dict[str, Any]:
    """Return a normalised copy, or raise SchemaError. Never mutates the input."""
    if not isinstance(doc, dict):
        raise SchemaError("config root must be a JSON object")

    out = _deep_copy(doc)

    version = out.get("schemaVersion")
    if version != SCHEMA_VERSION:
        raise SchemaError(
            f"schemaVersion {version!r} is not supported (this build writes {SCHEMA_VERSION})"
        )

    preset = out.get("preset")
    if preset not in PRESETS:
        raise SchemaError(f"preset {preset!r} is not a known preset")

    tokens = out.get("tokens")
    if not isinstance(tokens, dict):
        raise SchemaError("tokens must be an object")

    color = tokens.get("color")
    if not isinstance(color, dict):
        raise SchemaError("tokens.color must be an object")
    for key in REQUIRED_COLORS:
        if key not in color:
            raise SchemaError(f"tokens.color.{key} is required")
        color[key] = normalize_hex(color[key], f"tokens.color.{key}")

    typ = tokens.get("type")
    if not isinstance(typ, dict):
        raise SchemaError("tokens.type must be an object")
    for role in ("display", "body"):
        spec = typ.get(role)
        if not isinstance(spec, dict):
            raise SchemaError(f"tokens.type.{role} must be an object")
        family = spec.get("family")
        if not isinstance(family, str) or not family.strip():
            raise SchemaError(f"tokens.type.{role}.family must be a non-empty string")
        spec["family"] = family.strip()
        weights = spec.get("weights")
        if not isinstance(weights, list) or not weights:
            raise SchemaError(f"tokens.type.{role}.weights must be a non-empty array")
        clean_w = []
        for w in weights:
            if not isinstance(w, int) or isinstance(w, bool) or not 100 <= w <= 900:
                raise SchemaError(
                    f"tokens.type.{role}.weights: {w!r} is not a weight between 100 and 900"
                )
            clean_w.append(w)
        spec["weights"] = clean_w

    scale = typ.get("scale")
    if not isinstance(scale, list) or len(scale) < 3:
        raise SchemaError("tokens.type.scale must be an array of at least 3 sizes")
    clean_scale = []
    for s in scale:
        if isinstance(s, bool) or not isinstance(s, (int, float)) or s <= 0:
            raise SchemaError(f"tokens.type.scale: {s!r} is not a positive size")
        clean_scale.append(s)
    if clean_scale != sorted(clean_scale):
        raise SchemaError("tokens.type.scale must be ascending")
    typ["scale"] = clean_scale

    radius = tokens.get("radius")
    if not isinstance(radius, dict):
        raise SchemaError("tokens.radius must be an object")
    for key in REQUIRED_RADII:
        val = radius.get(key)
        if not isinstance(val, str) or not re.match(r"^\d+(?:\.\d+)?(px|rem|%)$", val):
            raise SchemaError(f"tokens.radius.{key} must be a CSS length like '4px'")

    spacing = tokens.get("spacing")
    if not isinstance(spacing, dict) or not isinstance(spacing.get("base"), (int, float)):
        raise SchemaError("tokens.spacing.base must be a number")
    if isinstance(spacing["base"], bool) or spacing["base"] <= 0:
        raise SchemaError("tokens.spacing.base must be positive")

    if not isinstance(tokens.get("shadow"), str):
        raise SchemaError("tokens.shadow must be a string ('none' is valid)")

    avoid = out.get("avoid")
    if not isinstance(avoid, list) or not all(isinstance(a, str) for a in avoid):
        raise SchemaError("avoid must be an array of strings")

    refs = out.get("references")
    if not isinstance(refs, list):
        raise SchemaError("references must be an array")
    for ref in refs:
        if not isinstance(ref, dict) or not isinstance(ref.get("path"), str):
            raise SchemaError("each reference needs a string 'path'")
        if "note" in ref and not isinstance(ref["note"], str):
            raise SchemaError("reference 'note' must be a string")

    meta = out.get("meta")
    if not isinstance(meta, dict) or not isinstance(meta.get("createdAt"), str):
        raise SchemaError("meta.createdAt is required")
    meta.setdefault("tool", "lookbook")

    return out


# --------------------------------------------------------------------------
# Read / write
# --------------------------------------------------------------------------


def read_config(project: str) -> dict[str, Any] | None:
    """Return the validated config, or None if absent/unreadable/invalid."""
    path = config_path(project)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    try:
        return validate(raw)
    except SchemaError:
        return None


def is_valid(project: str) -> bool:
    return read_config(project) is not None


def write_config(project: str, doc: dict[str, Any]) -> str:
    """Validate then write atomically. Returns the path written."""
    doc = validate(doc)
    path = config_path(project)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)
    return path
