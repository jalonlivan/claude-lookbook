# Preset token values

Full token values for every preset. `SKILL.md` stays short; this file is read
only when tokens actually need to be quoted or compared.

Generated from `scripts/schema.py`, which is the source of truth. If you edit
a value here, edit it there too -- the server serves `schema.PRESETS`, not this file.

---

## Two families

**`pigment`** puts the colour in the ink: a pale ground, a pigment accent,
elevation by shadow.

**`dark-dev`** puts the colour in the emission: a dark ground lit by one source,
with the interface built out of 1px hairline borders instead of shadows. That is
a different thing from dark mode, which is only a colour inversion. These pages
are *lit*: something glows, and everything else stays near-monochrome so the glow
reads. Lighting is the primary variable, which is why the picker asks for a
ground before it asks for a look.

| axis | values |
| --- | --- |
| `mode` | `light` / `dark` |
| `family` | `pigment` / `dark-dev` |
| `lighting.type` | `none` / `spot` / `field` / `wash` |
| `surface.elevation` | `border` / `shadow` / `both` |
| `density` | `marketing` / `catalog` / `console` |
| `motion.load` | `none` / `fade` / `staggered` |

`altMode` carries an optional palette for the opposite mode. It holds only the
groups that actually change with mode -- `color`, `ground`, `lighting`, `surface`
-- because type, radius, spacing, density and motion do not. **`altMode: null`
is an instruction, not an omission: that look has no other mode, so do not
invent one.**

The `avoid` list is **per-project and generated relative to the picked palette**:
entries that contradict the chosen accent or radius are dropped at build time,
and a lock line naming the exact accent is always appended. A global "never
purple" rule would be wrong -- plenty of brands are deliberately purple, and
`bloom` is exactly that. What the list forbids is the *default*, the colour
nobody chose. The two content rules (a narrow font stack, no em dashes) hold
across every preset: distinctive visuals paired with generic AI-tell prose is
still generic AI-tell prose.

---

# Family: `pigment`

## `editorial-warm` - Editorial Warm

Serif display, cream ground, one warm accent, near-zero radius.

| token | value |
| --- | --- |
| `mode` | `light` |
| `color.bg` | `#FBF3EF` |
| `color.surface` | `#FFFFFF` |
| `color.text` | `#1C1512` |
| `color.muted` | `#7A6A62` |
| `color.accent` | `#C2603F` |
| `color.border` | `#E8DBD3` |
| `ground` | base `#FBF3EF` · cast `none` |
| `lighting` | none · hue none · intensity 0.0 · position none · grain false |
| `surface` | elevation `border` · border `#E8DBD3` · raise `#FFFFFF` |
| `type.display` | Fraunces · 600, 900 |
| `type.body` | Source Sans 3 · 400, 600 |
| `type.mono` | IBM Plex Mono · 400 |
| `type.accentWord` | none |
| `type.scale` | 12, 14, 16, 20, 28, 44, 72 |
| `radius` | sm `2px` · md `4px` · lg `8px` · button `4px` |
| `spacing.base` | 8 |
| `shadow` | `none` |
| `density` | `marketing` |
| `motion` | load `fade` · stagger `0ms` · micro `minimal` |
| `altMode` | `null` - no other mode; do not invent one |

Base `avoid` list:

- Inter, Roboto, DM Sans
- em dashes in headings or body copy
- indigo/violet gradients
- glassmorphism and blur panels
- three equal-weight icon+heading+sentence cards
- gradient text
- pill-shaped buttons -- radius stays under 8px here
- pure #FFFFFF page background; the ground is cream

## `swiss-neutral` - Swiss Neutral

Grotesk, white and black, one accent, visible grid, generous whitespace.

| token | value |
| --- | --- |
| `mode` | `light` |
| `color.bg` | `#FFFFFF` |
| `color.surface` | `#F4F4F4` |
| `color.text` | `#0A0A0A` |
| `color.muted` | `#6E6E6E` |
| `color.accent` | `#D62828` |
| `color.border` | `#111111` |
| `ground` | base `#FFFFFF` · cast `none` |
| `lighting` | none · hue none · intensity 0.0 · position none · grain false |
| `surface` | elevation `border` · border `#111111` · raise `#F4F4F4` |
| `type.display` | Archivo · 500, 700 |
| `type.body` | IBM Plex Sans · 400, 600 |
| `type.mono` | IBM Plex Mono · 400 |
| `type.accentWord` | none |
| `type.scale` | 12, 14, 16, 18, 24, 36, 64 |
| `radius` | sm `0px` · md `0px` · lg `0px` · button `0px` |
| `spacing.base` | 8 |
| `shadow` | `none` |
| `density` | `marketing` |
| `motion` | load `fade` · stagger `0ms` · micro `minimal` |
| `altMode` | `null` - no other mode; do not invent one |

Base `avoid` list:

- Inter, Roboto, DM Sans
- em dashes in headings or body copy
- indigo/violet gradients
- any border-radius -- corners are square
- drop shadows and elevation layers
- centred hero text; this grid is left-aligned
- more than one accent colour

## `brutalist` - Brutalist

Weight extremes (200 vs 900), hard edges, one loud colour, no shadow.

| token | value |
| --- | --- |
| `mode` | `light` |
| `color.bg` | `#F2F0E6` |
| `color.surface` | `#FFFFFF` |
| `color.text` | `#000000` |
| `color.muted` | `#4A4A45` |
| `color.accent` | `#FF3B00` |
| `color.border` | `#000000` |
| `ground` | base `#F2F0E6` · cast `none` |
| `lighting` | none · hue none · intensity 0.0 · position none · grain false |
| `surface` | elevation `border` · border `#000000` · raise `#FFFFFF` |
| `type.display` | Space Grotesk · 300, 700 |
| `type.body` | Space Mono · 400, 700 |
| `type.mono` | Space Mono · 400, 700 |
| `type.accentWord` | none |
| `type.scale` | 12, 14, 16, 20, 32, 56, 96 |
| `radius` | sm `0px` · md `0px` · lg `0px` · button `0px` |
| `spacing.base` | 8 |
| `shadow` | `none` |
| `density` | `marketing` |
| `motion` | load `fade` · stagger `0ms` · micro `minimal` |
| `altMode` | `null` - no other mode; do not invent one |

Base `avoid` list:

- Inter, Roboto, DM Sans
- em dashes in headings or body copy
- indigo/violet gradients
- soft shadows, blur, glassmorphism
- mid-weight type -- use 300 or 700, nothing between
- rounded corners
- muted pastel accents

## `dark-luxe` - Dark Luxe

Near-black ground, thin type, image-led, minimal chrome.

| token | value |
| --- | --- |
| `mode` | `dark` |
| `color.bg` | `#0B0B0C` |
| `color.surface` | `#141416` |
| `color.text` | `#EDEAE4` |
| `color.muted` | `#8C877E` |
| `color.accent` | `#C8A45C` |
| `color.border` | `#26252A` |
| `ground` | base `#0B0B0C` · cast `none` |
| `lighting` | none · hue none · intensity 0.0 · position none · grain false |
| `surface` | elevation `border` · border `#26252A` · raise `#141416` |
| `type.display` | Cormorant Garamond · 300, 500 |
| `type.body` | Jost · 300, 500 |
| `type.mono` | IBM Plex Mono · 400 |
| `type.accentWord` | none |
| `type.scale` | 12, 14, 16, 20, 30, 48, 80 |
| `radius` | sm `0px` · md `2px` · lg `4px` · button `2px` |
| `spacing.base` | 8 |
| `shadow` | `none` |
| `density` | `marketing` |
| `motion` | load `fade` · stagger `0ms` · micro `minimal` |
| `altMode` | `null` - no other mode; do not invent one |

Base `avoid` list:

- Inter, Roboto, DM Sans
- em dashes in headings or body copy
- indigo/violet gradients
- neon or saturated accents; the accent is a muted metallic
- bold weights above 500
- card grids with borders on every side
- glow effects

## `product-dense` - Product Dense

Muted low-saturation, tight radii, high information density, full state coverage.

| token | value |
| --- | --- |
| `mode` | `light` |
| `color.bg` | `#FAFAF9` |
| `color.surface` | `#FFFFFF` |
| `color.text` | `#18181B` |
| `color.muted` | `#71717A` |
| `color.accent` | `#2F6F5E` |
| `color.border` | `#E4E4E7` |
| `ground` | base `#FAFAF9` · cast `none` |
| `lighting` | none · hue none · intensity 0.0 · position none · grain false |
| `surface` | elevation `shadow` · border `#E4E4E7` · raise `#FFFFFF` |
| `type.display` | Public Sans · 600, 700 |
| `type.body` | Public Sans · 400, 500 |
| `type.mono` | IBM Plex Mono · 400 |
| `type.accentWord` | none |
| `type.scale` | 11, 12, 13, 14, 16, 20, 28 |
| `radius` | sm `2px` · md `4px` · lg `6px` · button `4px` |
| `spacing.base` | 4 |
| `shadow` | `0 1px 2px rgba(24,24,27,0.06)` |
| `density` | `console` |
| `motion` | load `fade` · stagger `0ms` · micro `minimal` |
| `altMode` | `null` - no other mode; do not invent one |

Base `avoid` list:

- Inter, Roboto, DM Sans
- em dashes in headings or body copy
- indigo/violet gradients
- marketing-scale type; body text stays at 13-14px
- decorative hero sections
- tables without loading, empty and error states
- spacing above 24px between related controls

## `custom` - Custom

Your own palette, fonts and reference images.

| token | value |
| --- | --- |
| `mode` | `light` |
| `color.bg` | `#FFFFFF` |
| `color.surface` | `#F6F6F6` |
| `color.text` | `#111111` |
| `color.muted` | `#6B6B6B` |
| `color.accent` | `#C15F3C` |
| `color.border` | `#E2E2E2` |
| `ground` | base `#FFFFFF` · cast `none` |
| `lighting` | none · hue none · intensity 0.0 · position none · grain false |
| `surface` | elevation `border` · border `#E2E2E2` · raise `#F6F6F6` |
| `type.display` | Space Grotesk · 500, 700 |
| `type.body` | IBM Plex Sans · 400, 600 |
| `type.mono` | IBM Plex Mono · 400 |
| `type.accentWord` | none |
| `type.scale` | 12, 14, 16, 20, 28, 44, 72 |
| `radius` | sm `2px` · md `4px` · lg `8px` · button `4px` |
| `spacing.base` | 8 |
| `shadow` | `none` |
| `density` | `marketing` |
| `motion` | load `fade` · stagger `0ms` · micro `minimal` |
| `altMode` | `null` - no other mode; do not invent one |

Base `avoid` list:

- Inter, Roboto, DM Sans
- em dashes in headings or body copy
- indigo/violet gradients
- glassmorphism and blur panels
- three equal-weight icon+heading+sentence cards
- gradient text

---

# Family: `dark-dev`

## `console` - Console

Flat dark app chrome, hairline borders, one restrained accent, full state coverage.

| token | value |
| --- | --- |
| `mode` | `dark` |
| `color.bg` | `#0C0C0E` |
| `color.surface` | `#16161A` |
| `color.text` | `#ECECEE` |
| `color.muted` | `#94949B` |
| `color.accent` | `#7F56D9` |
| `color.border` | `#26262B` |
| `ground` | base `#0C0C0E` · cast `none` |
| `lighting` | none · hue none · intensity 0.0 · position none · grain false |
| `surface` | elevation `border` · border `rgba(255,255,255,0.08)` · raise `rgba(255,255,255,0.03)` |
| `type.display` | Geist · 500, 600 |
| `type.body` | Geist · 400, 500 |
| `type.mono` | Geist Mono · 400 |
| `type.accentWord` | none |
| `type.scale` | 11, 12, 13, 14, 16, 20, 28 |
| `radius` | sm `4px` · md `6px` · lg `8px` · button `6px` |
| `spacing.base` | 4 |
| `shadow` | `none` |
| `density` | `console` |
| `motion` | load `fade` · stagger `0ms` · micro `minimal` |
| `altMode` | `light` palette provided |

Base `avoid` list:

- Inter, Roboto, DM Sans
- em dashes in headings or body copy
- drop shadows for elevation; this family lifts with 1px hairline borders
- marketing-scale type; body text stays at 13-14px
- tables without loading, empty, error and disabled states
- decorative gradients; this preset is deliberately unlit
- accent colour anywhere except selection and the primary action

## `void` - Void

Pure black, one spotlit chromatic object, geometric grotesk, pill buttons, logo wall.

| token | value |
| --- | --- |
| `mode` | `dark` |
| `color.bg` | `#000000` |
| `color.surface` | `#0A0A0A` |
| `color.text` | `#EDEDED` |
| `color.muted` | `#A1A1A1` |
| `color.accent` | `#FFFFFF` |
| `color.border` | `#2E2E2E` |
| `ground` | base `#000000` · cast `none` |
| `lighting` | spot · hue #FF0080, #7928CA, #0070F3, #50E3C2 · intensity 0.75 · position center · grain false |
| `surface` | elevation `border` · border `rgba(255,255,255,0.10)` · raise `rgba(255,255,255,0.03)` |
| `type.display` | Geist · 400, 600 |
| `type.body` | Geist · 400, 500 |
| `type.mono` | Geist Mono · 400 |
| `type.accentWord` | none |
| `type.scale` | 12, 14, 16, 20, 32, 56, 96 |
| `radius` | sm `4px` · md `8px` · lg `12px` · button `999px` |
| `spacing.base` | 8 |
| `shadow` | `none` |
| `density` | `marketing` |
| `motion` | load `staggered` · stagger `60ms` · micro `minimal` |
| `altMode` | `light` palette provided |

Base `avoid` list:

- Inter, Roboto, DM Sans
- em dashes in headings or body copy
- drop shadows for elevation; this family lifts with 1px hairline borders
- a second lit element; one object glows and nothing else does
- colour anywhere but the glow and the logo wall stays monochrome
- timid type jumps; the scale steps 32 to 56 to 96 for a reason
- off-black backgrounds; the ground is #000000 exactly

## `bloom` - Bloom

Near-black with a grained aurora, monospace code panel, saturated pill CTA.

> Purple on purpose. The avoid list forbids the default nobody chose; picking this is the act of choosing.

| token | value |
| --- | --- |
| `mode` | `dark` |
| `color.bg` | `#060507` |
| `color.surface` | `#0F0D14` |
| `color.text` | `#F4F1FA` |
| `color.muted` | `#A1A1AA` |
| `color.accent` | `#A855F7` |
| `color.border` | `#241C33` |
| `ground` | base `#060507` · cast `#1A0B2E` |
| `lighting` | field · hue #A855F7, #4C1D95 · intensity 0.7 · position bottom-left · grain true |
| `surface` | elevation `border` · border `rgba(255,255,255,0.08)` · raise `rgba(255,255,255,0.04)` |
| `type.display` | Instrument Sans · 500, 700 |
| `type.body` | Instrument Sans · 400, 500 |
| `type.mono` | Azeret Mono · 400, 500 |
| `type.accentWord` | none |
| `type.scale` | 12, 14, 16, 20, 30, 48, 80 |
| `radius` | sm `6px` · md `10px` · lg `16px` · button `999px` |
| `spacing.base` | 8 |
| `shadow` | `none` |
| `density` | `marketing` |
| `motion` | load `staggered` · stagger `60ms` · micro `standard` |
| `altMode` | `null` - no other mode; do not invent one |

Base `avoid` list:

- Inter, Roboto, DM Sans
- em dashes in headings or body copy
- drop shadows for elevation; this family lifts with 1px hairline borders
- a clean gradient; the aurora needs grain or it bands and reads cheap
- a second aurora; one light source only
- syntax themes that fight the accent; the code panel stays near-monochrome

## `platform` - Platform

Deep navy, soft glow behind dimensional objects, one saturated CTA that is not the glow.

| token | value |
| --- | --- |
| `mode` | `dark` |
| `color.bg` | `#0D1117` |
| `color.surface` | `#161B22` |
| `color.text` | `#F0F6FC` |
| `color.muted` | `#8B949E` |
| `color.accent` | `#2DA44E` |
| `color.border` | `#30363D` |
| `ground` | base `#0D1117` · cast `#2A1A5E` |
| `lighting` | spot · hue #A371F7, #DB6BCB · intensity 0.55 · position center · grain false |
| `surface` | elevation `border` · border `rgba(255,255,255,0.10)` · raise `rgba(255,255,255,0.04)` |
| `type.display` | Mona Sans · 500, 700 |
| `type.body` | Mona Sans · 400, 600 |
| `type.mono` | JetBrains Mono · 400, 500 |
| `type.accentWord` | none |
| `type.scale` | 12, 14, 16, 20, 28, 44, 72 |
| `radius` | sm `4px` · md `6px` · lg `12px` · button `6px` |
| `spacing.base` | 8 |
| `shadow` | `none` |
| `density` | `marketing` |
| `motion` | load `staggered` · stagger `60ms` · micro `minimal` |
| `altMode` | `light` palette provided |

Base `avoid` list:

- Inter, Roboto, DM Sans
- em dashes in headings or body copy
- drop shadows for elevation; this family lifts with 1px hairline borders
- an accent that matches the glow; the CTA colour and the light are different colours
- pill-shaped buttons; this look uses a 6px rectangle
- flat vector spot illustration; the lit objects read as dimensional

## `gallery` - Gallery

Navy washing to blue, one italic serif word in a sans headline, a grid of work.

| token | value |
| --- | --- |
| `mode` | `dark` |
| `color.bg` | `#070C18` |
| `color.surface` | `#101827` |
| `color.text` | `#F8FAFC` |
| `color.muted` | `#94A3B8` |
| `color.accent` | `#3B82F6` |
| `color.border` | `#1E293B` |
| `ground` | base `#070C18` · cast `#1D4ED8` |
| `lighting` | wash · hue #1D4ED8, #070C18 · intensity 0.5 · position bottom · grain false |
| `surface` | elevation `border` · border `rgba(255,255,255,0.09)` · raise `rgba(255,255,255,0.03)` |
| `type.display` | Instrument Sans · 500, 600 |
| `type.body` | Instrument Sans · 400, 500 |
| `type.mono` | IBM Plex Mono · 400 |
| `type.accentWord` | Instrument Serif italic - one word per headline, maximum |
| `type.scale` | 12, 14, 16, 20, 28, 44, 72 |
| `radius` | sm `4px` · md `8px` · lg `12px` · button `999px` |
| `spacing.base` | 8 |
| `shadow` | `none` |
| `density` | `catalog` |
| `motion` | load `staggered` · stagger `60ms` · micro `minimal` |
| `altMode` | `null` - no other mode; do not invent one |

Base `avoid` list:

- Inter, Roboto, DM Sans
- em dashes in headings or body copy
- drop shadows for elevation; this family lifts with 1px hairline borders
- the serif on more than one word per headline
- a flat ground; the wash runs navy at the top to blue at the bottom
- card grids without a filter row above them

---

## Why these looks

The pigment presets optimise for expressive marketing pages, except
`product-dense`, which exists because dashboards, tables and settings live or
die on density and state coverage (loading, empty, error), which "be
distinctive" does not address.

In the dark-dev family, `console` plays that role and is the most demanding of
the five: if the token set can express hairline borders, selection states and a
dense table, the rest of the family is easy.

`custom` is the strongest path, not a fallback. A picture beats prose because it
stops the model falling back on a familiar archetype. When a config carries
`references[]`, read every image before writing markup.

