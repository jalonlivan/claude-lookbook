# Preset token values

Full token values for every preset. `SKILL.md` stays short; this file is read
only when tokens actually need to be quoted or compared.

Generated from `scripts/schema.py`, which is the source of truth. If you edit
a value here, edit it there too -- the server serves `schema.PRESETS`, not this file.

Every preset also carries an `avoid` list. The list is **per-project and generated
relative to the picked palette**: entries that contradict the chosen accent or radius
are dropped at build time, and a lock line naming the exact accent is always appended.
A global "never purple" rule would be wrong -- plenty of brands are deliberately
purple. What the list forbids is the *default*, the colour nobody chose.

---

## `editorial-warm` — Editorial Warm

Serif display, cream ground, one warm accent, near-zero radius.

| token | value |
| --- | --- |
| `color.bg` | `#FBF3EF` |
| `color.surface` | `#FFFFFF` |
| `color.text` | `#1C1512` |
| `color.muted` | `#7A6A62` |
| `color.accent` | `#C2603F` |
| `color.border` | `#E8DBD3` |
| `type.display` | Fraunces · 600, 900 |
| `type.body` | Source Sans 3 · 400, 600 |
| `type.scale` | 12, 14, 16, 20, 28, 44, 72 |
| `radius` | sm `2px` · md `4px` · lg `8px` |
| `spacing.base` | 8 |
| `shadow` | `none` |

Base `avoid` list:

- Inter, Roboto, DM Sans
- indigo/violet gradients
- glassmorphism and blur panels
- three equal-weight icon+heading+sentence cards
- gradient text
- pill-shaped buttons -- radius stays under 8px here
- pure #FFFFFF page background; the ground is cream

## `swiss-neutral` — Swiss Neutral

Grotesk, white and black, one accent, visible grid, generous whitespace.

| token | value |
| --- | --- |
| `color.bg` | `#FFFFFF` |
| `color.surface` | `#F4F4F4` |
| `color.text` | `#0A0A0A` |
| `color.muted` | `#6E6E6E` |
| `color.accent` | `#D62828` |
| `color.border` | `#111111` |
| `type.display` | Archivo · 500, 700 |
| `type.body` | IBM Plex Sans · 400, 600 |
| `type.scale` | 12, 14, 16, 18, 24, 36, 64 |
| `radius` | sm `0px` · md `0px` · lg `0px` |
| `spacing.base` | 8 |
| `shadow` | `none` |

Base `avoid` list:

- Inter, Roboto, DM Sans
- indigo/violet gradients
- any border-radius -- corners are square
- drop shadows and elevation layers
- centred hero text; this grid is left-aligned
- more than one accent colour

## `brutalist` — Brutalist

Weight extremes (200 vs 900), hard edges, one loud colour, no shadow.

| token | value |
| --- | --- |
| `color.bg` | `#F2F0E6` |
| `color.surface` | `#FFFFFF` |
| `color.text` | `#000000` |
| `color.muted` | `#4A4A45` |
| `color.accent` | `#FF3B00` |
| `color.border` | `#000000` |
| `type.display` | Space Grotesk · 300, 700 |
| `type.body` | Space Mono · 400, 700 |
| `type.scale` | 12, 14, 16, 20, 32, 56, 96 |
| `radius` | sm `0px` · md `0px` · lg `0px` |
| `spacing.base` | 8 |
| `shadow` | `none` |

Base `avoid` list:

- Inter, Roboto, DM Sans
- indigo/violet gradients
- soft shadows, blur, glassmorphism
- mid-weight type -- use 300 or 700, nothing between
- rounded corners
- muted pastel accents

## `dark-luxe` — Dark Luxe

Near-black ground, thin type, image-led, minimal chrome.

| token | value |
| --- | --- |
| `color.bg` | `#0B0B0C` |
| `color.surface` | `#141416` |
| `color.text` | `#EDEAE4` |
| `color.muted` | `#8C877E` |
| `color.accent` | `#C8A45C` |
| `color.border` | `#26252A` |
| `type.display` | Cormorant Garamond · 300, 500 |
| `type.body` | Jost · 300, 500 |
| `type.scale` | 12, 14, 16, 20, 30, 48, 80 |
| `radius` | sm `0px` · md `2px` · lg `4px` |
| `spacing.base` | 8 |
| `shadow` | `none` |

Base `avoid` list:

- Inter, Roboto, DM Sans
- indigo/violet gradients
- neon or saturated accents; the accent is a muted metallic
- bold weights above 500
- card grids with borders on every side
- glow effects

## `product-dense` — Product Dense

Muted low-saturation, tight radii, high information density, full state coverage.

| token | value |
| --- | --- |
| `color.bg` | `#FAFAF9` |
| `color.surface` | `#FFFFFF` |
| `color.text` | `#18181B` |
| `color.muted` | `#71717A` |
| `color.accent` | `#2F6F5E` |
| `color.border` | `#E4E4E7` |
| `type.display` | Public Sans · 600, 700 |
| `type.body` | Public Sans · 400, 500 |
| `type.scale` | 11, 12, 13, 14, 16, 20, 28 |
| `radius` | sm `2px` · md `4px` · lg `6px` |
| `spacing.base` | 4 |
| `shadow` | `0 1px 2px rgba(24,24,27,0.06)` |

Base `avoid` list:

- Inter, Roboto, DM Sans
- indigo/violet gradients
- marketing-scale type; body text stays at 13-14px
- decorative hero sections
- tables without loading, empty and error states
- spacing above 24px between related controls

## `custom` — Custom

Your own palette, fonts and reference images.

| token | value |
| --- | --- |
| `color.bg` | `#FFFFFF` |
| `color.surface` | `#F6F6F6` |
| `color.text` | `#111111` |
| `color.muted` | `#6B6B6B` |
| `color.accent` | `#C15F3C` |
| `color.border` | `#E2E2E2` |
| `type.display` | Space Grotesk · 500, 700 |
| `type.body` | IBM Plex Sans · 400, 600 |
| `type.scale` | 12, 14, 16, 20, 28, 44, 72 |
| `radius` | sm `2px` · md `4px` · lg `8px` |
| `spacing.base` | 8 |
| `shadow` | `none` |

Base `avoid` list:

- Inter, Roboto, DM Sans
- indigo/violet gradients
- glassmorphism and blur panels
- three equal-weight icon+heading+sentence cards
- gradient text

---

## Why these five

The first four optimise for expressive marketing pages. `product-dense` exists
because dashboards, tables and settings live or die on density and state coverage
(loading, empty, error), which "be distinctive" does not address.

`custom` is the strongest path, not a fallback. A picture beats prose because it
stops the model falling back on a familiar archetype. When a config carries
`references[]`, read every image before writing markup.

