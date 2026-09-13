---
name: mark
description: Generate a real logo and a complete favicon set - favicon.ico, every PNG size, apple-touch-icon, maskable PWA icons, SVG vector marks, site.webmanifest and the head snippet. Builds the mark from a font (wordmark or lettermark), from a procedural geometric shape, or from an image the user already has. Use when a site or app needs a logo, favicon, app icon, brand mark or wordmark, or when asked to replace CSS/Tailwind div-art with a real logo file. Reads .claude/branding.json so the mark matches the project's picked palette and display font.
---

# mark

Claude's usual reflex for a logo is a `<div>` with Tailwind classes: a coloured
square, a letter, maybe a gradient. That is not a logo. It cannot go in a
browser tab, an iOS home screen, a PWA manifest, an OG image, or a README.

`mark` produces the actual files.

---

## Run it

```bash
python <skill-dir>/scripts/mark.py --project . <mode> [options]
```

Three modes, same pipeline and the same outputs:

```bash
# 1. From a font -- wordmark plus an initials icon
python scripts/mark.py --project . text --text "Acme Supply" --font Georgia

# 2. From a procedural shape
python scripts/mark.py --project . shape --shape ring

# 3. From an image the user already has
python scripts/mark.py --project . image --image assets/logo.png
```

Exit 0 on success, exit 3 on bad arguments or an unwritable target.

### Before you run it

1. **Check `.claude/branding.json`.** If it exists, colours, the display font
   and the corner radius all come from it and the mark matches the rest of the
   site for free. If it does not, run lookbook first — or pass `--bg`/`--fg`
   explicitly.
2. **Ask which mode.** Do not guess. A user who has a logo file wants `image`;
   a user naming their product wants `text`; a user with neither wants `shape`.
3. **Check the font is installed.** `branding.json` names *webfonts*, which are
   usually not on the machine. `--list-fonts` shows what actually is.

```bash
python scripts/mark.py --list-fonts            # every installed family
python scripts/mark.py --list-fonts garamond   # filtered
python scripts/mark.py --list-shapes           # the procedural marks
```

Use `--dry-run` to show the user what would be written before writing it.

---

## What it writes

Into `public/`, `static/`, `www/` or `assets/` if one exists, else `brand/`.
Override with `--out`.

| file | what it is |
| --- | --- |
| `favicon.ico` | 16, 32 and 48 in one container, for the browser tab |
| `favicon-16x16.png` `favicon-32x32.png` `favicon-48x48.png` | modern tab icons |
| `apple-touch-icon.png` | 180px, **flattened opaque** — iOS composites alpha onto black |
| `icon-192.png` `icon-512.png` | PWA / Android |
| `icon-maskable-512.png` | extra safe-zone padding; Android crops icons to a circle |
| `mark.png` `mark.svg` | the bare square mark, transparent, no plate |
| `logo.png` `logo.svg` | text mode only: the full horizontal wordmark |
| `icon.svg` | the plated icon as vector |
| `site.webmanifest` | name, icons, theme and background colour |
| `head.html` | the `<link>` tags to paste into `<head>` |

The SVGs carry **real outline paths**, not `<text>` elements, so they render
identically everywhere without the font installed. Image mode produces no SVG —
rasters cannot be vectorised.

Existing files are never overwritten silently: the run stops and lists them.
Pass `--force` when the user wants them replaced.

---

## Options

```
--project DIR      project root (default: .)
--out DIR          output directory (default: public/ or static/, else brand/)

text mode:
  --text "Acme"      the wordmark
  --icon-text "AS"   what goes in the square icon
                     (default: initials of the first two words)
  --font NAME|PATH   family name, or a path to a .ttf
  --weight bold      100-900, or thin/light/regular/medium/semibold/bold/black
  --italic           prefer the italic cut
  --tracking 0.05    letter-spacing in em

image mode:
  --image PATH       PNG, GIF or BMP
  --no-trim          keep the source margins instead of cropping to the mark

shape mode:
  --shape ring       see --list-shapes

appearance:
  --bg #hex          plate colour      (default: accent from branding.json)
  --fg #hex          mark colour on the plate (default: auto-contrast)
  --ink #hex         mark colour standalone   (default: the plate colour)
  --plate rounded|circle|squircle|square|none
  --radius 0.22      plate corner radius as a fraction of its size
  --padding 0.18     space around the mark, 0-0.45

output:
  --name "Acme"      app name for the manifest
  --sizes 16,32,...  icon sizes
  --no-svg           skip the SVG files
  --no-manifest      skip site.webmanifest and head.html
  --force            overwrite existing files
  --dry-run          list what would be written
```

---

## Judgement calls worth making

- **A wordmark is not a favicon.** "Acme Supply" is illegible at 16px. Text mode
  already splits these: the wordmark goes to `logo.svg`, initials go in the
  icon. Do not fight it by forcing the full name into the square.
- **Wide source images make bad icons.** Image mode warns above 2.5:1. Take the
  warning seriously and offer a square crop or text mode instead.
- **Trimming is on by default** because exported logos are usually a small mark
  floating in a big transparent frame. `--no-trim` if the margin is deliberate.
- **Let contrast be chosen for you.** `--fg` defaults to whichever of the
  brand's own colours is actually legible on the plate. Override only when the
  user asks for a specific colour.
- **Square-cornered brands get square icons.** The plate radius is derived from
  `tokens.radius.lg`, so a brutalist or swiss-neutral pick does not get a soft
  app-store squircle.

---

## Contract with lookbook

One-way, in the direction lookbook's spec describes: mark reads
`.claude/branding.json` and never writes it.

```markdown
1. Check for `.claude/branding.json`.
2. If missing, run lookbook first so the mark matches the site.
3. Read the tokens. Use them exactly.
```

Nothing here depends on lookbook being installed — without a branding file,
mark falls back to a neutral dark plate and says so.

---

## Notes for the maintainer

Python 3 stdlib only. No pip, no npm, no build step. Four modules, each
independently testable:

| module | responsibility |
| --- | --- |
| `imgio.py` | PNG encode/decode, GIF and BMP decode, ICO write |
| `raster.py` | antialiased scanline fill, resampling, plates, procedural shapes |
| `fonts.py` | TrueType parsing, glyph outlines, font discovery |
| `mark.py` | CLI and the compose/emit pipeline |

### Deliberate limits

- **CFF/PostScript outlines (most `.otf`) are not read.** Type 2 charstrings are
  a second outline format entirely. Those fonts raise a clear error naming the
  limitation rather than rendering something wrong. TrueType `.ttf` and `.ttc`
  work, including composite glyphs and variable-font default instances.
- **JPEG and WebP input are rejected.** JPEG has no alpha and its ringing lands
  exactly on the hard edges a logo is made of. The error names the fix.
- **SVG input is rejected** — rasterising it would need a full SVG engine.
- **No kerning.** `hmtx` advances only; `GPOS` is not read. `--tracking` is the
  knob a logo actually needs.
- **No hinting.** 16px icons are box-filtered down from a large master, which is
  what image editors do; true 16px hinting is out of scope.

### Implementation notes

- Style matching uses the numeric `OS/2` weight class and `fsSelection` flags,
  never the subfamily string. On a localised Windows that string reads
  "Negreta", not "Bold", and string matching silently fails.
- The name table is read preferring the US-English record for the same reason.
- Font discovery reads only the table directory plus `name` and `OS/2` — reading
  each file whole to list families cost seconds, and `glyf` is never consulted.
- Downsampling goes through a mip pyramid with alpha premultiplied once.
  Resampling each size straight from the master was ~7× slower, and
  un-premultiplied averaging gives every edge a dark halo.
- `--render-size` is raised automatically to the largest requested icon, so an
  icon is never upscaled from a smaller master.
