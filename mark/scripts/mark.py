#!/usr/bin/env python3
"""mark -- generate a logo and a complete favicon set.

Three sources, one pipeline:

    mark.py --project . text  --text "Acme" --font Fraunces
    mark.py --project . image --image assets/logo.png
    mark.py --project . shape --shape ring

Colours, the display font and the corner radius default to whatever
`.claude/branding.json` says, so the mark matches the direction a human already
picked. Python 3 stdlib only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fonts  # noqa: E402
import imgio  # noqa: E402
import raster  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    try:  # a CJK font name must not crash the tool on a cp1252 console
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

EXIT_OK = 0
EXIT_BADARGS = 3

DEFAULT_SIZES = (16, 32, 48, 180, 192, 512)
RENDER_SIZE = 512

# Fallbacks when there is no branding.json to read.
FALLBACK_PLATE = "#1E1E1E"
FALLBACK_INK = "#FFFFFF"


class MarkError(ValueError):
    pass


# ==========================================================================
# Branding
# ==========================================================================


def load_branding(project: str) -> dict | None:
    path = os.path.join(os.path.abspath(project), ".claude", "branding.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    return doc if isinstance(doc, dict) and "tokens" in doc else None


def radius_fraction(branding: dict | None) -> float:
    """Map the brand's largest radius onto an icon-plate corner radius.

    A brand that chose square corners gets a square icon; 8px lg lands near the
    22% that reads as the familiar rounded-app-icon.
    """
    if not branding:
        return 0.22
    raw = str(branding.get("tokens", {}).get("radius", {}).get("lg", "8px"))
    m = re.match(r"^(\d+(?:\.\d+)?)", raw)
    if not m:
        return 0.22
    px = float(m.group(1))
    return max(0.0, min(0.5, px / 36.0))


def resolve_colors(args, branding):
    """Plate colour, mark colour on the plate, and standalone ink colour."""
    tokens = (branding or {}).get("tokens", {}).get("color", {})

    plate = args.bg or tokens.get("accent") or FALLBACK_PLATE
    plate_rgba = raster.parse_hex(plate)

    if args.fg:
        fg_rgba = raster.parse_hex(args.fg)
    elif tokens:
        # Whichever of the brand's own light/dark is actually legible on the plate.
        options = [
            raster.parse_hex(tokens.get("bg", "#FFFFFF")),
            raster.parse_hex(tokens.get("text", "#111111")),
            raster.parse_hex(tokens.get("surface", "#FFFFFF")),
        ]
        fg_rgba = raster.best_contrast(plate_rgba, options)
    else:
        fg_rgba = raster.best_contrast(
            plate_rgba, [raster.parse_hex("#FFFFFF"), raster.parse_hex("#111111")]
        )

    ink_rgba = raster.parse_hex(args.ink) if args.ink else plate_rgba
    return plate_rgba, fg_rgba, ink_rgba


# ==========================================================================
# Sources -- each returns contours in a `size` box, or a raster canvas
# ==========================================================================


def source_text(args, size: float, text: str):
    """Fit `text` inside a `size` box, centred on its inked bounds."""
    font = load_font(args)
    probe, w, h = fonts.layout(font, text, 100.0, args.tracking)
    if w <= 0 or h <= 0:
        raise MarkError(f"{text!r} has no visible outline in {font.family}")

    scale = min(size / w, size / h)
    dx = (size - w * scale) / 2
    dy = (size - h * scale) / 2
    return [[(x * scale + dx, y * scale + dy) for x, y in c] for c in probe]


def load_font(args) -> fonts.Font:
    query = args.font
    from_branding = False
    if not query:
        branding = args.branding
        if branding:
            query = (
                branding.get("tokens", {})
                .get("type", {})
                .get("display", {})
                .get("family")
            )
            from_branding = bool(query)
        if not query:
            raise MarkError(
                "no font given and no branding.json to read one from. "
                "Pass --font 'Family Name' or a path to a .ttf file."
            )
    try:
        return fonts.find_font(query, args.weight, args.italic)
    except fonts.FontError as exc:
        if from_branding:
            # The brand names a webfont; this machine only has what is installed.
            raise MarkError(
                f"{exc}\n"
                f"  {query!r} came from .claude/branding.json, which names webfonts "
                "rather than local ones.\n"
                f"  Either install {query}, download its .ttf and pass "
                "--font path/to/file.ttf,\n"
                "  or pick a local stand-in with --font 'Family Name'."
            ) from None
        raise


def source_shape(args, size: float):
    return raster.logomark(args.shape, size)


def source_image(args, size: float, canvas_size: int):
    """Decode the user's image and fit it, aspect preserved, into a size box."""
    with open(args.image, "rb") as fh:
        data = fh.read()
    sw, sh, rgba = imgio.decode_image(data)
    if sw < 2 or sh < 2:
        raise MarkError(f"{args.image} is {sw}x{sh}; that is not a logo")

    args.source_size = (sw, sh)
    if args.trim:
        rgba, sw, sh, cropped = raster.trim(rgba, sw, sh)
        args.trimmed = (sw, sh) if cropped else None
    else:
        args.trimmed = None

    dw, dh = raster.fit_box(sw, sh, size)
    scaled = raster.resize(rgba, sw, sh, dw, dh)

    layer = raster.Canvas(canvas_size, canvas_size)
    ox = (canvas_size - dw) // 2
    oy = (canvas_size - dh) // 2
    for y in range(dh):
        src = y * dw * 4
        dst = ((y + oy) * canvas_size + ox) * 4
        layer.px[dst : dst + dw * 4] = scaled[src : src + dw * 4]
    return layer, (sw, sh)


# ==========================================================================
# Compose
# ==========================================================================


def compose(args, canvas_size: int, padding: float, plated: bool):
    """Build one square canvas: optional plate, then the mark centred on it."""
    plate_rgba, fg_rgba, _ink = args.colors
    canvas = raster.Canvas(canvas_size, canvas_size)

    if plated and args.plate != "none":
        raster.fill(
            canvas,
            raster.plate(args.plate, canvas_size, args.radius),
            plate_rgba,
            args.samples,
        )

    inner = canvas_size * (1 - 2 * padding)
    offset = canvas_size * padding

    if args.mode == "image":
        layer, _ = source_image(args, inner, canvas_size)
        canvas.draw_over(layer)
        return canvas

    if args.mode == "text":
        contours = source_text(args, inner, args.icon_text)
    else:
        contours = source_shape(args, inner)

    shifted = [[(x + offset, y + offset) for x, y in c] for c in contours]
    raster.fill(canvas, shifted, fg_rgba if plated else _ink, args.samples)
    return canvas


def compose_wordmark(args, height: int):
    """The horizontal lockup: full text, transparent, ink colour."""
    font = load_font(args)
    contours, w, h = fonts.layout(font, args.text, height * 0.72, args.tracking)
    pad = height * 0.14
    width = int(round(w + pad * 2))
    canvas = raster.Canvas(width, height)
    dy = (height - h) / 2
    shifted = [[(x + pad, y + dy) for x, y in c] for c in contours]
    raster.fill(canvas, shifted, args.colors[2], args.samples)
    return canvas, shifted, width, height


# ==========================================================================
# SVG
# ==========================================================================


def svg_document(width, height, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img">\n{body}\n</svg>\n'
    )


def icon_svg(args, size: int = 512) -> str:
    plate_rgba, fg_rgba, _ = args.colors
    body = []

    if args.plate != "none":
        plate_path = raster.contours_to_svg_path(raster.plate(args.plate, size, args.radius))
        body.append(f'  <path d="{plate_path}" fill="{raster.to_hex(plate_rgba)}"/>')

    inner = size * (1 - 2 * args.padding)
    offset = size * args.padding
    contours = (
        source_text(args, inner, args.icon_text)
        if args.mode == "text"
        else source_shape(args, inner)
    )
    shifted = [[(x + offset, y + offset) for x, y in c] for c in contours]
    mark = raster.contours_to_svg_path(shifted)
    colour = fg_rgba if args.plate != "none" else args.colors[2]
    body.append(f'  <path d="{mark}" fill="{raster.to_hex(colour)}" fill-rule="nonzero"/>')
    return svg_document(size, size, "\n".join(body))


def mark_svg(args, size: int = 512) -> str:
    """The bare square mark on transparent ground, no plate."""
    ink = raster.to_hex(args.colors[2])
    inner = size * (1 - 2 * args.padding)
    offset = size * args.padding
    contours = (
        source_text(args, inner, args.icon_text)
        if args.mode == "text"
        else source_shape(args, inner)
    )
    shifted = [[(x + offset, y + offset) for x, y in c] for c in contours]
    path = raster.contours_to_svg_path(shifted)
    return svg_document(size, size, f'  <path d="{path}" fill="{ink}" fill-rule="nonzero"/>')


def wordmark_svg(args) -> str:
    """The full horizontal lockup, text mode only."""
    ink = raster.to_hex(args.colors[2])
    font = load_font(args)
    contours, w, h = fonts.layout(font, args.text, 100.0, args.tracking)
    path = raster.contours_to_svg_path(contours)
    return svg_document(
        int(round(w)), int(round(h)),
        f'  <path d="{path}" fill="{ink}" fill-rule="nonzero"/>',
    )


# ==========================================================================
# Output
# ==========================================================================


def pick_out_dir(project: str) -> str:
    """Favour the framework's real static root over inventing a new folder."""
    for candidate in ("public", "static", "www", "assets"):
        path = os.path.join(project, candidate)
        if os.path.isdir(path):
            return path
    return os.path.join(project, "brand")


def manifest(args, name: str) -> str:
    plate, _fg, _ink = args.colors
    # The splash background is the page ground, not the accent -- a full screen
    # of accent colour is not what the brand looks like.
    tokens = (args.branding or {}).get("tokens", {}).get("color", {})
    background = tokens.get("bg") or raster.to_hex(plate)
    short = name if len(name) <= 12 else name.split()[0][:12]
    doc = {
        "name": name,
        "short_name": short,
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {
                "src": "/icon-maskable-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable",
            },
        ],
        "theme_color": raster.to_hex(plate),
        "background_color": raster.to_hex(raster.parse_hex(background)),
        "display": "standalone",
    }
    return json.dumps(doc, indent=2) + "\n"


HEAD_SNIPPET = """<!-- Generated by mark. Paste into <head>. Paths assume these
     files sit at the web root; adjust if they are served from a subpath. -->
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">{svg_line}
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<meta name="theme-color" content="{theme}">
"""


def build(args) -> list[tuple[str, bytes]]:
    """Everything the run will write, as (relative path, bytes)."""
    out: list[tuple[str, bytes]] = []
    canvas_size = args.render_size

    master = compose(args, canvas_size, args.padding, plated=True)
    pyramid = raster.Pyramid(master.to_rgba(), canvas_size, floor=min(args.sizes))

    png_by_size: dict[int, bytes] = {}
    for size in args.sizes:
        scaled = pyramid.at(size)
        if size == 180:  # iOS composites alpha onto black; hand it an opaque icon
            tmp = raster.Canvas(size, size)
            tmp.px = bytearray(scaled)
            scaled = tmp.flatten_onto(args.colors[0]).to_rgba()
        png_by_size[size] = imgio.encode_png(size, size, scaled)

    for size in args.sizes:
        if size == 180:
            out.append(("apple-touch-icon.png", png_by_size[size]))
        elif size in (192, 512):
            out.append((f"icon-{size}.png", png_by_size[size]))
        else:
            out.append((f"favicon-{size}x{size}.png", png_by_size[size]))

    ico_sizes = [s for s in (16, 32, 48) if s in png_by_size]
    if ico_sizes:
        out.append(("favicon.ico", imgio.encode_ico([(s, png_by_size[s]) for s in ico_sizes])))

    # Maskable: Android crops to a circle, so the mark needs a wider safe zone.
    maskable = compose(args, canvas_size, min(0.42, args.padding + 0.12), plated=True)
    mask_rgba = raster.resize(maskable.to_rgba(), canvas_size, canvas_size, 512, 512)
    flat = raster.Canvas(512, 512)
    flat.px = bytearray(mask_rgba)
    out.append(
        ("icon-maskable-512.png", imgio.encode_png(512, 512, flat.flatten_onto(args.colors[0]).to_rgba()))
    )

    # The bare square mark, transparent and unplated.
    bare = compose(args, canvas_size, args.padding, plated=False)
    bare_512 = raster.resize(bare.to_rgba(), canvas_size, canvas_size, 512, 512)
    out.append(("mark.png", imgio.encode_png(512, 512, bare_512)))

    # In text mode the primary logo is the full wordmark, not the initials.
    if args.mode == "text":
        word_canvas, _c, w, h = compose_wordmark(args, 256)
        out.append(("logo.png", imgio.encode_png(w, h, word_canvas.to_rgba())))

    if args.svg and args.mode != "image":
        out.append(("icon.svg", icon_svg(args).encode("utf-8")))
        out.append(("mark.svg", mark_svg(args).encode("utf-8")))
        if args.mode == "text":
            out.append(("logo.svg", wordmark_svg(args).encode("utf-8")))

    if args.manifest:
        out.append(("site.webmanifest", manifest(args, args.name).encode("utf-8")))
        svg_line = (
            '\n<link rel="icon" type="image/svg+xml" href="/icon.svg">'
            if args.svg and args.mode != "image"
            else ""
        )
        out.append((
            "head.html",
            HEAD_SNIPPET.format(svg_line=svg_line, theme=raster.to_hex(args.colors[0])).encode("utf-8"),
        ))

    return out


# ==========================================================================
# CLI
# ==========================================================================


class Parser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write(f"mark: {message}\n")
        self.print_usage(sys.stderr)
        raise SystemExit(EXIT_BADARGS)


def build_parser() -> Parser:
    p = Parser(prog="mark.py", description="Generate a logo and a full favicon set.")
    p.add_argument("mode", nargs="?", choices=("text", "image", "shape"),
                   help="where the mark comes from")
    p.add_argument("--project", default=".", help="project directory (default: .)")
    p.add_argument("--out", help="output directory (default: public/ or static/, else brand/)")

    p.add_argument("--text", help="text mode: the wordmark, e.g. 'Acme'")
    p.add_argument("--icon-text", help="text mode: what goes in the square icon "
                                       "(default: initials of the first two words)")
    p.add_argument("--font", help="family name or path to a .ttf "
                                  "(default: display family from branding.json)")
    p.add_argument("--weight", help="100-900, or thin/light/regular/medium/semibold/bold/black")
    p.add_argument("--italic", action="store_true", help="prefer the italic cut")
    p.add_argument("--tracking", type=float, default=0.0, help="letter-spacing in em")

    p.add_argument("--image", help="image mode: path to a PNG, GIF or BMP")
    p.add_argument("--no-trim", dest="trim", action="store_false",
                   help="image mode: keep the source margins instead of cropping to the mark")
    p.add_argument("--shape", help=f"shape mode: one of {', '.join(raster.SHAPES)}")

    p.add_argument("--bg", help="plate colour (default: accent from branding.json)")
    p.add_argument("--fg", help="mark colour on the plate (default: auto-contrast)")
    p.add_argument("--ink", help="mark colour standalone (default: the plate colour)")
    p.add_argument("--plate", default=None, choices=raster.PLATES, help="plate shape")
    p.add_argument("--radius", type=float, default=None,
                   help="plate corner radius as a fraction, 0-0.5 "
                        "(default: derived from branding.json radius.lg)")
    p.add_argument("--padding", type=float, default=0.18,
                   help="space around the mark as a fraction, 0-0.45 (default 0.18)")

    p.add_argument("--name", help="app name for the manifest (default: the text, else the folder)")
    p.add_argument("--sizes", default=",".join(str(s) for s in DEFAULT_SIZES),
                   help="comma-separated icon sizes")
    p.add_argument("--render-size", type=int, default=RENDER_SIZE,
                   help="master canvas size before downsampling")
    p.add_argument("--samples", type=int, default=4, help="antialiasing sub-scanlines")
    p.add_argument("--no-svg", dest="svg", action="store_false", help="skip the SVG output")
    p.add_argument("--no-manifest", dest="manifest", action="store_false",
                   help="skip site.webmanifest and head.html")
    p.add_argument("--force", action="store_true", help="overwrite existing files")
    p.add_argument("--dry-run", action="store_true", help="list what would be written")

    p.add_argument("--list-fonts", nargs="?", const="", metavar="QUERY",
                   help="list installed families and exit")
    p.add_argument("--list-shapes", action="store_true", help="list procedural shapes and exit")
    return p


def list_fonts(query: str) -> int:
    faces = fonts.scan_fonts()
    if not faces:
        print("mark: no readable TrueType fonts found in", ", ".join(fonts.font_dirs()) or "(no font dirs)")
        return EXIT_OK

    needle = "".join(c for c in query.lower() if c.isalnum())
    families: dict[str, list] = {}
    for f in faces:
        if needle and needle not in "".join(c for c in f.family.lower() if c.isalnum()):
            continue
        families.setdefault(f.family, []).append(f)

    if not families:
        print(f"mark: nothing matching {query!r} among {len(faces)} installed faces.")
        return EXIT_OK

    print(f"{len(families)} famil{'y' if len(families)==1 else 'ies'}"
          + (f" matching {query!r}" if query else "") + ":\n")
    for family in sorted(families):
        cuts = families[family]
        styles = sorted({f"{f.subfamily}" for f in cuts})
        weights = sorted({f.weight for f in cuts})
        print(f"  {family}")
        print(f"      styles: {', '.join(styles[:8])}")
        print(f"      weights: {', '.join(str(w) for w in weights)}")
    print("\nUse any family name with --font, or pass a path to a .ttf file.")
    return EXIT_OK


def derive_icon_text(text: str) -> str:
    """Initials of up to two words. A 12-letter wordmark is mush at 16px."""
    words = [w for w in re.split(r"[\s\-_]+", text.strip()) if w]
    if not words:
        raise MarkError("--text is empty")
    if len(words) == 1:
        return words[0][:2] if len(words[0]) <= 2 else words[0][0]
    return (words[0][0] + words[1][0]).upper()


def validate(args) -> None:
    if not args.mode:
        raise MarkError("pick a mode: text, image or shape (see --help)")

    if args.mode == "text":
        if not args.text:
            raise MarkError("text mode needs --text")
        args.icon_text = args.icon_text or derive_icon_text(args.text)
    elif args.mode == "image":
        if not args.image:
            raise MarkError("image mode needs --image")
        if not os.path.isfile(args.image):
            raise MarkError(f"no such image: {args.image}")
    else:
        if not args.shape:
            raise MarkError(f"shape mode needs --shape (one of {', '.join(raster.SHAPES)})")
        if args.shape not in raster.SHAPES:
            raise MarkError(f"unknown shape {args.shape!r}; choose from {', '.join(raster.SHAPES)}")

    if not 0 <= args.padding <= 0.45:
        raise MarkError("--padding must be between 0 and 0.45")
    if args.radius is not None and not 0 <= args.radius <= 0.5:
        raise MarkError("--radius must be between 0 and 0.5")
    if not 1 <= args.samples <= 16:
        raise MarkError("--samples must be between 1 and 16")
    if not 64 <= args.render_size <= 4096:
        raise MarkError("--render-size must be between 64 and 4096")

    try:
        args.sizes = sorted({int(s) for s in args.sizes.split(",") if s.strip()})
    except ValueError:
        raise MarkError("--sizes must be comma-separated integers")
    if not args.sizes:
        raise MarkError("--sizes is empty")
    if any(s < 8 or s > 1024 for s in args.sizes):
        raise MarkError("icon sizes must be between 8 and 1024")
    # Never upscale: the master must be at least as large as the biggest icon.
    args.render_size = max(args.render_size, max(args.sizes))


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_shapes:
        print("Procedural shapes (--shape):\n")
        for name in raster.SHAPES:
            print(f"  {name}")
        print("\nEach is built to survive 16x16: one idea, thick strokes, no fine detail.")
        return EXIT_OK
    if args.list_fonts is not None:
        return list_fonts(args.list_fonts)

    project = os.path.abspath(args.project)
    if not os.path.isdir(project):
        sys.stderr.write(f"mark: not a directory: {project}\n")
        return EXIT_BADARGS

    try:
        validate(args)
    except MarkError as exc:
        sys.stderr.write(f"mark: {exc}\n")
        return EXIT_BADARGS

    args.branding = load_branding(project)
    if args.plate is None:
        args.plate = "rounded"
    if args.radius is None:
        args.radius = radius_fraction(args.branding)

    try:
        args.colors = resolve_colors(args, args.branding)
    except ValueError as exc:
        sys.stderr.write(f"mark: {exc}\n")
        return EXIT_BADARGS

    args.name = args.name or args.text or os.path.basename(project) or "App"

    out_dir = os.path.abspath(args.out) if args.out else pick_out_dir(project)

    try:
        files = build(args)
    except (MarkError, fonts.FontError, imgio.ImageError, ValueError) as exc:
        sys.stderr.write(f"mark: {exc}\n")
        return EXIT_BADARGS
    except OSError as exc:
        sys.stderr.write(f"mark: {exc}\n")
        return EXIT_BADARGS

    # Report the decisions before touching disk -- these are the values another
    # skill has to match, and the ones most likely to be wrong.
    plate, fg, ink = args.colors
    print(f"mark: {args.mode} mode -> {out_dir}")
    if args.branding:
        print(f"  branding: {args.branding.get('preset', '?')} from .claude/branding.json")
    else:
        print("  branding: none found; run lookbook first for brand-matched colours")
    if args.mode == "text":
        font = load_font(args)
        print(f"  font: {font.family} {font.subfamily}  ({os.path.basename(font.path)})")
        print(f"  wordmark: {args.text!r}   icon: {args.icon_text!r}")
    elif args.mode == "shape":
        print(f"  shape: {args.shape}")
    else:
        src = getattr(args, "source_size", None)
        trimmed = getattr(args, "trimmed", None)
        detail = f"{src[0]}x{src[1]}" if src else "?"
        if trimmed:
            detail += f" -> trimmed to {trimmed[0]}x{trimmed[1]}"
        print(f"  image: {args.image}  ({detail})")
        shape = trimmed or src
        if shape and shape[1] and shape[0] / shape[1] > 2.5:
            print(
                "  note: this mark is wider than 2.5:1, so it will be unreadable at "
                "16px.\n        Consider a square crop, or text mode with --icon-text."
            )
    print(f"  plate: {args.plate} r={args.radius:.2f} {raster.to_hex(plate)}"
          f"   mark: {raster.to_hex(fg)}   ink: {raster.to_hex(ink)}")

    existing = [n for n, _ in files if os.path.exists(os.path.join(out_dir, n))]
    if existing and not args.force and not args.dry_run:
        sys.stderr.write(
            "mark: these already exist in "
            + out_dir
            + ":\n    "
            + "\n    ".join(existing)
            + "\n  Re-run with --force to overwrite them.\n"
        )
        return EXIT_BADARGS

    if args.dry_run:
        print(f"\n  would write {len(files)} files:")
        for name, blob in files:
            print(f"    {name:26s} {len(blob):>7,} bytes")
        return EXIT_OK

    try:
        os.makedirs(out_dir, exist_ok=True)
        for name, blob in files:
            path = os.path.join(out_dir, name)
            with open(path, "wb") as fh:
                fh.write(blob)
    except OSError as exc:
        sys.stderr.write(f"mark: could not write into {out_dir}: {exc}\n")
        return EXIT_BADARGS

    print()
    for name, blob in files:
        print(f"WROTE: {os.path.join(out_dir, name)}  ({len(blob):,} bytes)")
    if args.manifest:
        print("\nPaste head.html into your <head>. Files are referenced from the web root.")
    return EXIT_OK


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(EXIT_BADARGS)
