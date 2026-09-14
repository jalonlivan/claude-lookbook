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

SCHEMA_VERSION = 2

CONFIG_RELPATH = os.path.join(".claude", "branding.json")
REFS_RELDIR = os.path.join(".claude", "branding", "refs")

HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
LENGTH_RE = re.compile(r"^\d+(?:\.\d+)?(px|rem|%)$")
DURATION_RE = re.compile(r"^\d+(?:\.\d+)?(ms|s)$")

# --------------------------------------------------------------------------
# v2 vocabulary
#
# Two preset families. `pigment` looks put the colour in the ink: a light
# ground, a coloured accent, elevation by shadow. `dark-dev` looks put the
# colour in the emission: a dark ground, one light source, elevation by 1px
# hairline border. That is a different thing from "dark mode", which is only a
# colour inversion, and it is why the family gets its own axis rather than five
# more cards in the same grid.
# --------------------------------------------------------------------------

MODES = ("light", "dark")
FAMILIES = ("pigment", "dark-dev")

# How the page is lit. The primary variable in the dark-dev family.
LIGHTING_TYPES = (
    "none",   # flat. app chrome.
    "spot",   # one object lit from behind
    "field",  # a large aurora or bloom occupying a third of the viewport
    "wash",   # ambient page-level gradient with no visible source
)
LIGHT_POSITIONS = (
    "center", "top", "bottom", "left", "right",
    "top-left", "top-right", "bottom-left", "bottom-right", "diagonal",
)

# Where elevation comes from. "border" is the highest-leverage token in the
# dark-dev family: getting shadows out of the output does more than any colour.
ELEVATIONS = ("border", "shadow", "both")

DENSITIES = ("marketing", "catalog", "console")

MOTION_LOADS = ("none", "fade", "staggered")
MOTION_MICRO = ("minimal", "standard", "expressive")

DEFAULT_MONO = "IBM Plex Mono"

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
            "density": "console",
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
    # ----------------------------------------------------------------------
    # dark-dev family. A dark ground, lit by a light source, with the interface
    # built out of borders instead of shadows.
    # ----------------------------------------------------------------------
    "console": {
        "label": "Console",
        "blurb": "Flat dark app chrome, hairline borders, one restrained accent, full state coverage.",
        "mode": "dark",
        "family": "dark-dev",
        "tokens": {
            "color": {
                "bg": "#0C0C0E",
                "surface": "#16161A",
                "text": "#ECECEE",
                "muted": "#94949B",
                "accent": "#7F56D9",
                "border": "#26262B",
            },
            "ground": {"base": "#0C0C0E", "cast": None},
            "lighting": {
                "type": "none",
                "hue": [],
                "intensity": 0.0,
                "position": None,
                "grain": False,
            },
            "surface": {
                "elevation": "border",
                "border": "rgba(255,255,255,0.08)",
                "raise": "rgba(255,255,255,0.03)",
            },
            "type": {
                "display": {"family": "Geist", "weights": [500, 600]},
                "body": {"family": "Geist", "weights": [400, 500]},
                "mono": {"family": "Geist Mono", "weights": [400]},
                "accentWord": None,
                "scale": [11, 12, 13, 14, 16, 20, 28],
            },
            "radius": {"sm": "4px", "md": "6px", "lg": "8px", "button": "6px"},
            "spacing": {"base": 4},
            "shadow": "none",
            "density": "console",
            "motion": {"load": "fade", "stagger": "0ms", "micro": "minimal"},
        },
        # An app needs a light mode; this look survives one.
        "altMode": {
            "mode": "light",
            "color": {
                "bg": "#FFFFFF",
                "surface": "#FAFAFA",
                "text": "#181D27",
                "muted": "#535862",
                "accent": "#7F56D9",
                "border": "#E9EAEB",
            },
            "ground": {"base": "#FFFFFF", "cast": None},
            "lighting": {
                "type": "none",
                "hue": [],
                "intensity": 0.0,
                "position": None,
                "grain": False,
            },
            "surface": {
                "elevation": "border",
                "border": "rgba(0,0,0,0.08)",
                "raise": "rgba(0,0,0,0.02)",
            },
        },
        "avoid": [
            "Inter, Roboto, DM Sans",
            "em dashes in headings or body copy",
            "drop shadows for elevation; this family lifts with 1px hairline borders",
            "marketing-scale type; body text stays at 13-14px",
            "tables without loading, empty, error and disabled states",
            "decorative gradients; this preset is deliberately unlit",
            "accent colour anywhere except selection and the primary action",
        ],
    },
    "void": {
        "label": "Void",
        "blurb": "Pure black, one spotlit chromatic object, geometric grotesk, pill buttons, logo wall.",
        "mode": "dark",
        "family": "dark-dev",
        "tokens": {
            "color": {
                "bg": "#000000",
                "surface": "#0A0A0A",
                "text": "#EDEDED",
                "muted": "#A1A1A1",
                "accent": "#FFFFFF",
                "border": "#2E2E2E",
            },
            "ground": {"base": "#000000", "cast": None},
            "lighting": {
                "type": "spot",
                "hue": ["#FF0080", "#7928CA", "#0070F3", "#50E3C2"],
                "intensity": 0.75,
                "position": "center",
                "grain": False,
            },
            "surface": {
                "elevation": "border",
                "border": "rgba(255,255,255,0.10)",
                "raise": "rgba(255,255,255,0.03)",
            },
            "type": {
                "display": {"family": "Geist", "weights": [400, 600]},
                "body": {"family": "Geist", "weights": [400, 500]},
                "mono": {"family": "Geist Mono", "weights": [400]},
                "accentWord": None,
                "scale": [12, 14, 16, 20, 32, 56, 96],
            },
            "radius": {"sm": "4px", "md": "8px", "lg": "12px", "button": "999px"},
            "spacing": {"base": 8},
            "shadow": "none",
            "density": "marketing",
            "motion": {"load": "staggered", "stagger": "60ms", "micro": "minimal"},
        },
        "altMode": {
            "mode": "light",
            "color": {
                "bg": "#FFFFFF",
                "surface": "#FAFAFA",
                "text": "#000000",
                "muted": "#666666",
                "accent": "#000000",
                "border": "#EAEAEA",
            },
            "ground": {"base": "#FFFFFF", "cast": None},
            "lighting": {
                "type": "spot",
                "hue": ["#FF0080", "#7928CA", "#0070F3", "#50E3C2"],
                "intensity": 0.35,
                "position": "center",
                "grain": False,
            },
            "surface": {
                "elevation": "border",
                "border": "rgba(0,0,0,0.08)",
                "raise": "rgba(0,0,0,0.02)",
            },
        },
        "avoid": [
            "Inter, Roboto, DM Sans",
            "em dashes in headings or body copy",
            "drop shadows for elevation; this family lifts with 1px hairline borders",
            "a second lit element; one object glows and nothing else does",
            "colour anywhere but the glow and the logo wall stays monochrome",
            "timid type jumps; the scale steps 32 to 56 to 96 for a reason",
            "off-black backgrounds; the ground is #000000 exactly",
        ],
    },
    "bloom": {
        "label": "Bloom",
        "blurb": "Near-black with a grained aurora, monospace code panel, saturated pill CTA.",
        # Shown under the card. Without it, the one preset that is deliberately
        # purple looks like the bug this whole tool exists to prevent.
        "note": "Purple on purpose. The avoid list forbids the default nobody "
                "chose; picking this is the act of choosing.",
        "mode": "dark",
        "family": "dark-dev",
        "tokens": {
            "color": {
                "bg": "#060507",
                "surface": "#0F0D14",
                "text": "#F4F1FA",
                "muted": "#A1A1AA",
                "accent": "#A855F7",
                "border": "#241C33",
            },
            "ground": {"base": "#060507", "cast": "#1A0B2E"},
            "lighting": {
                "type": "field",
                "hue": ["#A855F7", "#4C1D95"],
                "intensity": 0.70,
                "position": "bottom-left",
                "grain": True,
            },
            "surface": {
                "elevation": "border",
                "border": "rgba(255,255,255,0.08)",
                "raise": "rgba(255,255,255,0.04)",
            },
            "type": {
                "display": {"family": "Instrument Sans", "weights": [500, 700]},
                "body": {"family": "Instrument Sans", "weights": [400, 500]},
                "mono": {"family": "Azeret Mono", "weights": [400, 500]},
                "accentWord": None,
                "scale": [12, 14, 16, 20, 30, 48, 80],
            },
            "radius": {"sm": "6px", "md": "10px", "lg": "16px", "button": "999px"},
            "spacing": {"base": 8},
            "shadow": "none",
            "density": "marketing",
            "motion": {"load": "staggered", "stagger": "60ms", "micro": "standard"},
        },
        # The aurora is the identity. On white it is not the same look.
        "altMode": None,
        # Purple is deliberate here and only here, so the indigo/violet line is
        # absent from this list by design. The avoid list forbids the default
        # nobody chose; picking this preset is the act of choosing.
        "avoid": [
            "Inter, Roboto, DM Sans",
            "em dashes in headings or body copy",
            "drop shadows for elevation; this family lifts with 1px hairline borders",
            "a clean gradient; the aurora needs grain or it bands and reads cheap",
            "a second aurora; one light source only",
            "syntax themes that fight the accent; the code panel stays near-monochrome",
        ],
    },
    "platform": {
        "label": "Platform",
        "blurb": "Deep navy, soft glow behind dimensional objects, one saturated CTA that is not the glow.",
        "mode": "dark",
        "family": "dark-dev",
        "tokens": {
            "color": {
                "bg": "#0D1117",
                "surface": "#161B22",
                "text": "#F0F6FC",
                "muted": "#8B949E",
                "accent": "#2DA44E",
                "border": "#30363D",
            },
            "ground": {"base": "#0D1117", "cast": "#2A1A5E"},
            "lighting": {
                "type": "spot",
                "hue": ["#A371F7", "#DB6BCB"],
                "intensity": 0.55,
                "position": "center",
                "grain": False,
            },
            "surface": {
                "elevation": "border",
                "border": "rgba(255,255,255,0.10)",
                "raise": "rgba(255,255,255,0.04)",
            },
            "type": {
                "display": {"family": "Mona Sans", "weights": [500, 700]},
                "body": {"family": "Mona Sans", "weights": [400, 600]},
                "mono": {"family": "JetBrains Mono", "weights": [400, 500]},
                "accentWord": None,
                "scale": [12, 14, 16, 20, 28, 44, 72],
            },
            "radius": {"sm": "4px", "md": "6px", "lg": "12px", "button": "6px"},
            "spacing": {"base": 8},
            "shadow": "none",
            "density": "marketing",
            "motion": {"load": "staggered", "stagger": "60ms", "micro": "minimal"},
        },
        "altMode": {
            "mode": "light",
            "color": {
                "bg": "#FFFFFF",
                "surface": "#F6F8FA",
                "text": "#1F2328",
                "muted": "#59636E",
                "accent": "#1F883D",
                "border": "#D1D9E0",
            },
            "ground": {"base": "#FFFFFF", "cast": None},
            "lighting": {
                "type": "spot",
                "hue": ["#A371F7", "#DB6BCB"],
                "intensity": 0.30,
                "position": "center",
                "grain": False,
            },
            "surface": {
                "elevation": "border",
                "border": "rgba(0,0,0,0.10)",
                "raise": "rgba(0,0,0,0.03)",
            },
        },
        "avoid": [
            "Inter, Roboto, DM Sans",
            "em dashes in headings or body copy",
            "drop shadows for elevation; this family lifts with 1px hairline borders",
            "an accent that matches the glow; the CTA colour and the light are different colours",
            "pill-shaped buttons; this look uses a 6px rectangle",
            "flat vector spot illustration; the lit objects read as dimensional",
        ],
    },
    "gallery": {
        "label": "Gallery",
        "blurb": "Navy washing to blue, one italic serif word in a sans headline, a grid of work.",
        "mode": "dark",
        "family": "dark-dev",
        "tokens": {
            "color": {
                "bg": "#070C18",
                "surface": "#101827",
                "text": "#F8FAFC",
                "muted": "#94A3B8",
                "accent": "#3B82F6",
                "border": "#1E293B",
            },
            "ground": {"base": "#070C18", "cast": "#1D4ED8"},
            "lighting": {
                "type": "wash",
                "hue": ["#1D4ED8", "#070C18"],
                "intensity": 0.50,
                "position": "bottom",
                "grain": False,
            },
            "surface": {
                "elevation": "border",
                "border": "rgba(255,255,255,0.09)",
                "raise": "rgba(255,255,255,0.03)",
            },
            "type": {
                "display": {"family": "Instrument Sans", "weights": [500, 600]},
                "body": {"family": "Instrument Sans", "weights": [400, 500]},
                "mono": {"family": "IBM Plex Mono", "weights": [400]},
                "accentWord": {
                    "family": "Instrument Serif",
                    "style": "italic",
                    "use": "one word per headline, maximum",
                },
                "scale": [12, 14, 16, 20, 28, 44, 72],
            },
            "radius": {"sm": "4px", "md": "8px", "lg": "12px", "button": "999px"},
            "spacing": {"base": 8},
            "shadow": "none",
            "density": "catalog",
            "motion": {"load": "staggered", "stagger": "60ms", "micro": "minimal"},
        },
        # The navy-to-blue wash is the identity, not a theme setting.
        "altMode": None,
        "avoid": [
            "Inter, Roboto, DM Sans",
            "em dashes in headings or body copy",
            "drop shadows for elevation; this family lifts with 1px hairline borders",
            "the serif on more than one word per headline",
            "a flat ground; the wash runs navy at the top to blue at the bottom",
            "card grids without a filter row above them",
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

def _fill_v2_defaults(preset: dict[str, Any]) -> dict[str, Any]:
    """Give every preset a complete v2 token set.

    The pigment presets predate these groups, so rather than hand-copying eight
    new keys into five dicts, they are derived once here from what those presets
    already say. The same derivation is what migrates a v1 file on disk.
    """
    tokens = preset["tokens"]
    color = tokens["color"]

    preset.setdefault("mode", "dark" if _is_dark(color["bg"]) else "light")
    preset.setdefault("family", "pigment")
    preset.setdefault("altMode", None)

    tokens.setdefault("ground", {"base": color["bg"], "cast": None})
    tokens.setdefault(
        "lighting",
        {"type": "none", "hue": [], "intensity": 0.0, "position": None, "grain": False},
    )
    tokens.setdefault(
        "surface",
        {
            # A preset that already declares a shadow lifts with shadow; one that
            # does not was already lifting with its border.
            "elevation": "shadow" if tokens.get("shadow", "none") != "none" else "border",
            "border": color["border"],
            "raise": color["surface"],
        },
    )

    typ = tokens["type"]
    if "mono" not in typ:
        # A body face that is already monospaced is the preset's own mono.
        body = typ["body"]["family"]
        typ["mono"] = (
            {"family": body, "weights": list(typ["body"]["weights"])}
            if body.lower().endswith(("mono", "code"))
            else {"family": DEFAULT_MONO, "weights": [400]}
        )
    typ.setdefault("accentWord", None)

    tokens["radius"].setdefault("button", tokens["radius"]["md"])
    tokens.setdefault("density", "marketing")
    tokens.setdefault(
        "motion", {"load": "fade", "stagger": "0ms", "micro": "minimal"}
    )
    return preset


def _is_dark(hex_color: str) -> bool:
    """Self-contained on purpose: this runs at import time, before the helper
    section below has been defined."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)

    def lin(c: float) -> float:
        c /= 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b) < 0.18


for _p in PRESETS.values():
    _fill_v2_defaults(_p)

PRESET_NAMES = list(PRESETS.keys())

# The ground-first picker asks for this before it asks for a look.
DARK_PRESETS = [n for n, p in PRESETS.items() if p["mode"] == "dark"]
LIGHT_PRESETS = [n for n, p in PRESETS.items() if p["mode"] == "light"]

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
        "mode": base["mode"],
        "family": base["family"],
        "tokens": tokens,
        "altMode": base["altMode"],
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
    for group in ("color", "radius", "spacing", "ground", "lighting", "surface", "motion"):
        if isinstance(override.get(group), dict):
            out[group].update(override[group])
    if isinstance(override.get("type"), dict):
        t = override["type"]
        for role in ("display", "body", "mono"):
            if isinstance(t.get(role), dict):
                out["type"][role].update(t[role])
        if isinstance(t.get("scale"), list):
            out["type"]["scale"] = t["scale"]
        if "accentWord" in t:
            out["type"]["accentWord"] = t["accentWord"]
    if isinstance(override.get("shadow"), str):
        out["shadow"] = override["shadow"]
    if isinstance(override.get("density"), str):
        out["density"] = override["density"]
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

    # An older file is upgraded in place rather than rejected. A file from a
    # *future* version is still refused, since half-understanding it would
    # silently mis-render someone's brand.
    out = migrate(out)

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
    for role in ("display", "body", "mono"):
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

    # ---- v2 groups ----
    if out.get("mode") not in MODES:
        raise SchemaError(f"mode must be one of {', '.join(MODES)}")
    if out.get("family") not in FAMILIES:
        raise SchemaError(f"family must be one of {', '.join(FAMILIES)}")

    if not isinstance(typ.get("accentWord"), (dict, type(None))):
        raise SchemaError("tokens.type.accentWord must be an object or null")
    if isinstance(typ.get("accentWord"), dict):
        word = typ["accentWord"]
        if not isinstance(word.get("family"), str) or not word["family"].strip():
            raise SchemaError("tokens.type.accentWord.family must be a non-empty string")
        if word.get("style") not in ("normal", "italic"):
            raise SchemaError("tokens.type.accentWord.style must be 'normal' or 'italic'")
        word.setdefault("use", "one word per headline, maximum")

    if "button" in radius:
        val = radius["button"]
        if not isinstance(val, str) or not LENGTH_RE.match(val):
            raise SchemaError("tokens.radius.button must be a CSS length like '999px'")

    if tokens.get("density") not in DENSITIES:
        raise SchemaError(f"tokens.density must be one of {', '.join(DENSITIES)}")

    motion = tokens.get("motion")
    if not isinstance(motion, dict):
        raise SchemaError("tokens.motion must be an object")
    if motion.get("load") not in MOTION_LOADS:
        raise SchemaError(f"tokens.motion.load must be one of {', '.join(MOTION_LOADS)}")
    if motion.get("micro") not in MOTION_MICRO:
        raise SchemaError(f"tokens.motion.micro must be one of {', '.join(MOTION_MICRO)}")
    if not isinstance(motion.get("stagger"), str) or not DURATION_RE.match(motion["stagger"]):
        raise SchemaError("tokens.motion.stagger must be a duration like '60ms'")

    _validate_palette_groups(tokens, "tokens")

    alt = out.get("altMode")
    if alt is not None:
        if not isinstance(alt, dict):
            raise SchemaError("altMode must be an object or null")
        if alt.get("mode") not in MODES:
            raise SchemaError(f"altMode.mode must be one of {', '.join(MODES)}")
        if alt["mode"] == out["mode"]:
            raise SchemaError("altMode.mode must differ from the primary mode")
        alt_color = alt.get("color")
        if not isinstance(alt_color, dict):
            raise SchemaError("altMode.color must be an object")
        for key in REQUIRED_COLORS:
            if key not in alt_color:
                raise SchemaError(f"altMode.color.{key} is required")
            alt_color[key] = normalize_hex(alt_color[key], f"altMode.color.{key}")
        _validate_palette_groups(alt, "altMode")

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


def _validate_palette_groups(holder: dict[str, Any], where: str) -> None:
    """ground / lighting / surface. These three appear both in `tokens` and in
    `altMode`, because they are exactly the groups that change with mode --
    type, radius, spacing, density and motion do not."""
    ground = holder.get("ground")
    if not isinstance(ground, dict):
        raise SchemaError(f"{where}.ground must be an object")
    ground["base"] = normalize_hex(ground.get("base"), f"{where}.ground.base")
    if ground.get("cast") is not None:
        ground["cast"] = normalize_hex(ground["cast"], f"{where}.ground.cast")
    else:
        ground["cast"] = None

    lighting = holder.get("lighting")
    if not isinstance(lighting, dict):
        raise SchemaError(f"{where}.lighting must be an object")
    if lighting.get("type") not in LIGHTING_TYPES:
        raise SchemaError(
            f"{where}.lighting.type must be one of {', '.join(LIGHTING_TYPES)}"
        )
    hue = lighting.get("hue")
    if not isinstance(hue, list) or len(hue) > 6:
        raise SchemaError(f"{where}.lighting.hue must be an array of at most 6 colours")
    lighting["hue"] = [
        normalize_hex(h, f"{where}.lighting.hue[{i}]") for i, h in enumerate(hue)
    ]
    intensity = lighting.get("intensity")
    if isinstance(intensity, bool) or not isinstance(intensity, (int, float)):
        raise SchemaError(f"{where}.lighting.intensity must be a number 0-1")
    if not 0.0 <= intensity <= 1.0:
        raise SchemaError(f"{where}.lighting.intensity must be between 0 and 1")
    if lighting.get("position") is not None and lighting["position"] not in LIGHT_POSITIONS:
        raise SchemaError(
            f"{where}.lighting.position must be null or one of {', '.join(LIGHT_POSITIONS)}"
        )
    if not isinstance(lighting.get("grain"), bool):
        raise SchemaError(f"{where}.lighting.grain must be true or false")
    # A lit page with no hue cannot be rendered; an unlit one must not claim a hue.
    if lighting["type"] != "none" and not lighting["hue"]:
        raise SchemaError(f"{where}.lighting.type is {lighting['type']!r} but hue is empty")
    if lighting["type"] == "none" and lighting["intensity"]:
        raise SchemaError(f"{where}.lighting is 'none' but intensity is not 0")

    surface = holder.get("surface")
    if not isinstance(surface, dict):
        raise SchemaError(f"{where}.surface must be an object")
    if surface.get("elevation") not in ELEVATIONS:
        raise SchemaError(
            f"{where}.surface.elevation must be one of {', '.join(ELEVATIONS)}"
        )
    for key in ("border", "raise"):
        if not isinstance(surface.get(key), str) or not surface[key].strip():
            raise SchemaError(f"{where}.surface.{key} must be a CSS colour string")


def migrate(doc: dict[str, Any]) -> dict[str, Any]:
    """Bring an older config up to the current schema.

    v1 files predate every group the dark-dev family needs, so they are filled
    from what the file already says rather than rejected. A v1 install that
    upgrades keeps its look; it does not get sent back to the picker.
    """
    version = doc.get("schemaVersion")
    if version == SCHEMA_VERSION:
        return doc
    if version != 1:
        raise SchemaError(
            f"schemaVersion {version!r} is not supported (this build writes {SCHEMA_VERSION})"
        )

    out = _deep_copy(doc)
    out["schemaVersion"] = SCHEMA_VERSION
    # _fill_v2_defaults derives every new group from the v1 body, which is the
    # same derivation the shipped pigment presets go through at import.
    _fill_v2_defaults(out)
    out["meta"] = out.get("meta") or {}
    out["meta"]["migratedFrom"] = version
    return out


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
