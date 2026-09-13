"""Antialiased scanline rasteriser, resampling, and procedural mark shapes.

Stdlib only. Everything a mark is made of -- glyph outlines, plates, geometric
logomarks -- reduces to closed contours of points, which this module fills with
the nonzero winding rule.
"""

from __future__ import annotations

import math

Point = tuple[float, float]
Contour = list[Point]


# ==========================================================================
# Colour
# ==========================================================================


def parse_hex(value: str) -> tuple[int, int, int, int]:
    v = str(value).strip().lstrip("#")
    if len(v) in (3, 4):
        v = "".join(c * 2 for c in v)
    if len(v) == 6:
        v += "ff"
    if len(v) != 8 or any(c not in "0123456789abcdefABCDEF" for c in v):
        raise ValueError(f"{value!r} is not a hex colour like #E67D22")
    return tuple(int(v[i : i + 2], 16) for i in (0, 2, 4, 6))


def to_hex(rgba: tuple[int, int, int, int]) -> str:
    return "#%02X%02X%02X" % rgba[:3]


def relative_luminance(rgb: tuple[int, int, int, int]) -> float:
    def lin(c: float) -> float:
        c /= 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = rgb[0], rgb[1], rgb[2]
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast_ratio(a, b) -> float:
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def best_contrast(background, candidates):
    """Pick whichever candidate is most legible on `background`."""
    return max(candidates, key=lambda c: contrast_ratio(background, c))


# ==========================================================================
# Canvas
# ==========================================================================


class Canvas:
    __slots__ = ("w", "h", "px")

    def __init__(self, w: int, h: int, fill: tuple[int, int, int, int] | None = None):
        self.w, self.h = w, h
        if fill and fill[3]:
            self.px = bytearray(bytes(fill) * (w * h))
        else:
            self.px = bytearray(w * h * 4)  # transparent

    def clone(self) -> "Canvas":
        c = Canvas.__new__(Canvas)
        c.w, c.h, c.px = self.w, self.h, bytearray(self.px)
        return c

    def to_rgba(self) -> bytes:
        return bytes(self.px)

    def flatten_onto(self, rgb: tuple[int, int, int, int]) -> "Canvas":
        """Composite over an opaque colour. Needed for apple-touch-icon, which
        iOS renders on black if you hand it alpha."""
        out = Canvas(self.w, self.h, (rgb[0], rgb[1], rgb[2], 255))
        out.draw_over(self)
        return out

    def draw_over(self, top: "Canvas") -> None:
        """Standard source-over composite of `top` onto self."""
        if (top.w, top.h) != (self.w, self.h):
            raise ValueError("canvas size mismatch")
        dst, src = self.px, top.px
        for i in range(0, len(src), 4):
            sa = src[i + 3]
            if not sa:
                continue
            if sa == 255:
                dst[i : i + 4] = src[i : i + 4]
                continue
            ia = 255 - sa
            da = dst[i + 3]
            out_a = sa + da * ia // 255
            if not out_a:
                continue
            for k in range(3):
                s = src[i + k] * sa
                d = dst[i + k] * da * ia // 255
                dst[i + k] = (s + d) // out_a
            dst[i + 3] = out_a


# ==========================================================================
# Rasterise
# ==========================================================================


def coverage(contours: list[Contour], w: int, h: int, samples: int = 4):
    """Per-pixel coverage 0..1, nonzero winding rule.

    Sub-scanlines give vertical antialiasing; span ends are computed
    analytically for horizontal antialiasing. Edges are bucketed by starting
    row and swept with an active list, so cost tracks visible complexity
    rather than total outline complexity.
    """
    cov = [0.0] * (w * h)

    # (ytop, ybot, x_at_ytop, dxdy, winding)
    buckets: dict[int, list] = {}
    for contour in contours:
        n = len(contour)
        if n < 2:
            continue
        for i in range(n):
            x0, y0 = contour[i]
            x1, y1 = contour[(i + 1) % n]
            if y0 == y1:
                continue
            wind = 1
            if y0 > y1:
                x0, y0, x1, y1 = x1, y1, x0, y0
                wind = -1
            if y1 <= 0 or y0 >= h:
                continue
            dxdy = (x1 - x0) / (y1 - y0)
            row = max(0, int(math.floor(y0)))
            buckets.setdefault(row, []).append((y0, y1, x0, dxdy, wind))

    if not buckets:
        return cov, 0, 0

    weight = 1.0 / samples
    active: list = []
    first_row = min(buckets)
    last_row = min(h - 1, max(int(math.ceil(max(e[1] for es in buckets.values() for e in es))), 0))

    for y in range(first_row, min(h, last_row + 1)):
        if y in buckets:
            active += buckets[y]
        if not active:
            continue

        row_base = y * w
        for s in range(samples):
            sy = y + (s + 0.5) * weight
            hits = []
            for y0, y1, x0, dxdy, wind in active:
                if y0 <= sy < y1:
                    hits.append((x0 + (sy - y0) * dxdy, wind))
            if len(hits) < 2:
                continue
            hits.sort()

            winding = 0
            span_start = 0.0
            for x, wind in hits:
                was = winding
                winding += wind
                if was == 0 and winding != 0:
                    span_start = x
                elif was != 0 and winding == 0:
                    _add_span(cov, row_base, w, span_start, x, weight)

        # retire edges that end above the next row
        nxt = y + 1
        active = [e for e in active if e[1] > nxt]

    return cov, first_row, min(h, last_row + 1)


def _add_span(cov: list[float], base: int, w: int, x0: float, x1: float, weight: float):
    """Accumulate a horizontal span with fractional coverage at both ends."""
    if x1 <= x0:
        return
    x0 = max(x0, 0.0)
    x1 = min(x1, float(w))
    if x1 <= x0:
        return

    ix0, ix1 = int(x0), int(x1)
    if ix0 == ix1:
        cov[base + ix0] += (x1 - x0) * weight
        return

    cov[base + ix0] += (ix0 + 1 - x0) * weight
    for x in range(ix0 + 1, ix1):
        cov[base + x] += weight
    if ix1 < w:
        cov[base + ix1] += (x1 - ix1) * weight


def fill(canvas: Canvas, contours: list[Contour], color, samples: int = 4) -> None:
    """Composite `color` onto the canvas using the coverage of `contours`."""
    r, g, b, a = color
    if not a:
        return
    cov, y0, y1 = coverage(contours, canvas.w, canvas.h, samples)
    px = canvas.px
    for i in range(y0 * canvas.w, y1 * canvas.w):
        c = cov[i]
        if c <= 0.0:
            continue
        if c > 1.0:
            c = 1.0
        sa = int(a * c + 0.5)
        if not sa:
            continue
        o = i * 4
        if sa == 255:
            px[o] = r
            px[o + 1] = g
            px[o + 2] = b
            px[o + 3] = 255
            continue
        da = px[o + 3]
        ia = 255 - sa
        out_a = sa + da * ia // 255
        if not out_a:
            continue
        px[o] = (r * sa + px[o] * da * ia // 255) // out_a
        px[o + 1] = (g * sa + px[o + 1] * da * ia // 255) // out_a
        px[o + 2] = (b * sa + px[o + 2] * da * ia // 255) // out_a
        px[o + 3] = out_a


# ==========================================================================
# Resample
# ==========================================================================


def premultiply(rgba: bytes) -> list[float]:
    """Alpha must be premultiplied before averaging, or transparent pixels drag
    their (arbitrary) colour into the mean and every edge grows a dark halo."""
    pm = [0.0] * len(rgba)
    for i in range(0, len(rgba), 4):
        a = rgba[i + 3]
        if not a:
            continue
        f = a / 255.0
        pm[i] = rgba[i] * f
        pm[i + 1] = rgba[i + 1] * f
        pm[i + 2] = rgba[i + 2] * f
        pm[i + 3] = a
    return pm


def unpremultiply(pm: list[float], count: int) -> bytes:
    res = bytearray(count * 4)
    for i in range(0, count * 4, 4):
        a = pm[i + 3]
        if a <= 0.5:
            continue
        f = 255.0 / a
        res[i] = min(255, max(0, int(pm[i] * f + 0.5)))
        res[i + 1] = min(255, max(0, int(pm[i + 1] * f + 0.5)))
        res[i + 2] = min(255, max(0, int(pm[i + 2] * f + 0.5)))
        res[i + 3] = min(255, int(a + 0.5))
    return bytes(res)


def _halve(pm: list[float], w: int, h: int) -> list[float]:
    """Exact 2:1 box filter. Cheap, and an integer ratio means no aliasing."""
    dw, dh = w // 2, h // 2
    out = [0.0] * (dw * dh * 4)
    for y in range(dh):
        r0 = (y * 2) * w * 4
        r1 = r0 + w * 4
        o = y * dw * 4
        for x in range(dw):
            a = r0 + x * 8
            b = r1 + x * 8
            for k in range(4):
                out[o + k] = (pm[a + k] + pm[a + 4 + k] + pm[b + k] + pm[b + 4 + k]) * 0.25
            o += 4
    return out


def resample_pm(pm: list[float], sw: int, sh: int, dw: int, dh: int) -> list[float]:
    """Separable area-average on premultiplied data."""
    if (sw, sh) == (dw, dh):
        return pm
    tmp = [0.0] * (dw * sh * 4)
    _axis(pm, tmp, sw, sh, dw, horizontal=True)
    out = [0.0] * (dw * dh * 4)
    _axis(tmp, out, dw, sh, dh, horizontal=False)
    return out


def resize(rgba: bytes, sw: int, sh: int, dw: int, dh: int) -> bytes:
    if (sw, sh) == (dw, dh):
        return bytes(rgba)
    return unpremultiply(resample_pm(premultiply(rgba), sw, sh, dw, dh), dw * dh)


class Pyramid:
    """Mip chain over a square master.

    Resampling every output size straight from the master costs O(master) per
    size; halving once and resampling each target from the smallest level that
    still exceeds it costs a fraction of that, and the pre-filtered level also
    keeps near-1:1 ratios from aliasing.
    """

    def __init__(self, rgba: bytes, size: int, floor: int = 16):
        self.levels: dict[int, list[float]] = {size: premultiply(rgba)}
        s = size
        while s // 2 >= floor and s % 2 == 0:
            self.levels[s // 2] = _halve(self.levels[s], s, s)
            s //= 2
        self.sizes = sorted(self.levels)

    def at(self, target: int) -> bytes:
        source = next((s for s in self.sizes if s >= target), self.sizes[-1])
        pm = self.levels[source]
        if source == target:
            return unpremultiply(pm, target * target)
        return unpremultiply(
            resample_pm(pm, source, source, target, target), target * target
        )


def _axis(src, dst, sw, sh, dn, horizontal):
    """One pass of area-averaging along a single axis."""
    sn = sw if horizontal else sh
    scale = sn / dn
    rows = sh if horizontal else sw
    for d in range(dn):
        lo, hi = d * scale, (d + 1) * scale
        i0, i1 = int(lo), min(sn, int(math.ceil(hi)))
        weights = []
        total = 0.0
        for i in range(i0, i1):
            wgt = min(hi, i + 1) - max(lo, i)
            if wgt > 0:
                weights.append((i, wgt))
                total += wgt
        if total <= 0:
            weights, total = [(min(i0, sn - 1), 1.0)], 1.0

        for r in range(rows):
            acc = [0.0, 0.0, 0.0, 0.0]
            for i, wgt in weights:
                o = (r * sw + i) * 4 if horizontal else (i * sw + r) * 4
                acc[0] += src[o] * wgt
                acc[1] += src[o + 1] * wgt
                acc[2] += src[o + 2] * wgt
                acc[3] += src[o + 3] * wgt
            o = (r * dn + d) * 4 if horizontal else (d * sw + r) * 4
            dst[o] = acc[0] / total
            dst[o + 1] = acc[1] / total
            dst[o + 2] = acc[2] / total
            dst[o + 3] = acc[3] / total


def trim(rgba: bytes, w: int, h: int, tolerance: int = 8):
    """Crop empty margins off a source image.

    Exported logos are usually a small mark floating in a large frame. Fitting
    that whole frame into a square icon shrinks the mark until it is illegible,
    so trim to what is actually inked: the alpha bounding box when the image has
    transparency, otherwise the area differing from the border colour.

    Returns (rgba, w, h, cropped).
    """
    if w < 2 or h < 2:
        return rgba, w, h, False

    has_alpha = any(rgba[i] < 250 for i in range(3, len(rgba), 4))

    if has_alpha:
        def inked(x, y):
            return rgba[(y * w + x) * 4 + 3] > tolerance
    else:
        o = 0  # top-left pixel stands in for the background
        bg = (rgba[o], rgba[o + 1], rgba[o + 2])

        def inked(x, y):
            p = (y * w + x) * 4
            return (
                abs(rgba[p] - bg[0]) > tolerance
                or abs(rgba[p + 1] - bg[1]) > tolerance
                or abs(rgba[p + 2] - bg[2]) > tolerance
            )

    min_x, min_y, max_x, max_y = w, h, -1, -1
    for y in range(h):
        row = y * w
        for x in range(w):
            if inked(x, y):
                if x < min_x:
                    min_x = x
                if x > max_x:
                    max_x = x
                if y < min_y:
                    min_y = y
                max_y = y
        del row

    if max_x < 0 or max_y < 0:
        return rgba, w, h, False  # nothing inked; leave it alone
    if (min_x, min_y, max_x, max_y) == (0, 0, w - 1, h - 1):
        return rgba, w, h, False

    nw, nh = max_x - min_x + 1, max_y - min_y + 1
    out = bytearray(nw * nh * 4)
    for y in range(nh):
        src = ((y + min_y) * w + min_x) * 4
        dst = y * nw * 4
        out[dst : dst + nw * 4] = rgba[src : src + nw * 4]
    return bytes(out), nw, nh, True


def fit_box(sw: int, sh: int, box: float) -> tuple[int, int]:
    """Largest size fitting in a square box, aspect preserved."""
    if sw >= sh:
        return max(1, int(box)), max(1, int(round(box * sh / sw)))
    return max(1, int(round(box * sw / sh))), max(1, int(box))


# ==========================================================================
# Curves
# ==========================================================================


def flatten_quadratic(p0, p1, p2, steps: int = 12) -> list[Point]:
    out = []
    for i in range(1, steps + 1):
        t = i / steps
        u = 1 - t
        out.append(
            (
                u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
                u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1],
            )
        )
    return out


def flatten_cubic(p0, p1, p2, p3, steps: int = 16) -> list[Point]:
    out = []
    for i in range(1, steps + 1):
        t = i / steps
        u = 1 - t
        out.append(
            (
                u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
                u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1],
            )
        )
    return out


def arc(cx, cy, r, a0, a1, steps: int = 16) -> list[Point]:
    return [
        (cx + r * math.cos(a0 + (a1 - a0) * i / steps),
         cy + r * math.sin(a0 + (a1 - a0) * i / steps))
        for i in range(steps + 1)
    ]


# ==========================================================================
# Plates and marks
#
# All shapes live in a 0..1 box and are scaled by the caller, so the same
# definition serves a 16px favicon and a 512px PWA icon.
# ==========================================================================


def rounded_rect(x, y, w, h, r, steps: int = 12) -> Contour:
    r = max(0.0, min(r, min(w, h) / 2))
    if r <= 0:
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    pts: Contour = []
    pts += arc(x + w - r, y + r, r, -math.pi / 2, 0, steps)
    pts += arc(x + w - r, y + h - r, r, 0, math.pi / 2, steps)
    pts += arc(x + r, y + h - r, r, math.pi / 2, math.pi, steps)
    pts += arc(x + r, y + r, r, math.pi, math.pi * 1.5, steps)
    return pts


def circle(cx, cy, r, steps: int = 64) -> Contour:
    return arc(cx, cy, r, 0, math.tau, steps)[:-1]


def superellipse(cx, cy, rx, ry, n: float = 4.0, steps: int = 96) -> Contour:
    """The iOS-style squircle. n=2 is an ellipse, n=4 reads as a soft square."""
    pts: Contour = []
    for i in range(steps):
        t = math.tau * i / steps
        ct, st = math.cos(t), math.sin(t)
        pts.append(
            (
                cx + rx * math.copysign(abs(ct) ** (2 / n), ct),
                cy + ry * math.copysign(abs(st) ** (2 / n), st),
            )
        )
    return pts


def plate(kind: str, size: float, radius_frac: float = 0.22) -> list[Contour]:
    """Background plate for an icon, in a size x size box."""
    if kind == "none":
        return []
    if kind == "circle":
        return [circle(size / 2, size / 2, size / 2)]
    if kind == "squircle":
        return [superellipse(size / 2, size / 2, size / 2, size / 2)]
    if kind == "square":
        return [rounded_rect(0, 0, size, size, 0)]
    if kind == "rounded":
        return [rounded_rect(0, 0, size, size, size * radius_frac)]
    raise ValueError(f"unknown plate {kind!r}")


PLATES = ("rounded", "circle", "squircle", "square", "none")


def _poly(pts, size) -> Contour:
    return [(x * size, y * size) for x, y in pts]


def logomark(name: str, size: float) -> list[Contour]:
    """Procedural marks. Each is built to survive 16x16 -- one idea, thick
    strokes, no detail that dies under a box filter."""
    s = size
    half = s / 2

    if name == "ring":
        outer = circle(half, half, s * 0.40, 72)
        inner = circle(half, half, s * 0.22, 72)
        return [outer, inner[::-1]]  # reversed inner punches the hole

    if name == "dot":
        return [circle(half, half, s * 0.34, 72)]

    if name == "orbit":
        outer = circle(half, half, s * 0.40, 72)
        inner = circle(half, half, s * 0.28, 72)
        return [outer, inner[::-1], circle(half, half, s * 0.13, 48)]

    if name == "hexagon":
        r = s * 0.42
        return [[
            (half + r * math.cos(math.pi / 6 + math.tau * i / 6),
             half + r * math.sin(math.pi / 6 + math.tau * i / 6))
            for i in range(6)
        ]]

    if name == "triangle":
        return [_poly([(0.5, 0.10), (0.92, 0.84), (0.08, 0.84)], s)]

    if name == "diamond":
        return [_poly([(0.5, 0.06), (0.94, 0.5), (0.5, 0.94), (0.06, 0.5)], s)]

    if name == "chevron":
        return [_poly(
            [(0.22, 0.16), (0.50, 0.16), (0.80, 0.50), (0.50, 0.84),
             (0.22, 0.84), (0.52, 0.50)], s)]

    if name == "bars":
        return [
            rounded_rect(0.14 * s, 0.16 * s, 0.72 * s, 0.16 * s, 0.08 * s),
            rounded_rect(0.14 * s, 0.42 * s, 0.50 * s, 0.16 * s, 0.08 * s),
            rounded_rect(0.14 * s, 0.68 * s, 0.30 * s, 0.16 * s, 0.08 * s),
        ]

    if name == "arch":
        outer: Contour = [(0.16 * s, 0.86 * s), (0.16 * s, 0.46 * s)]
        outer += arc(half, 0.46 * s, 0.34 * s, math.pi, math.tau, 32)
        outer += [(0.84 * s, 0.86 * s), (0.66 * s, 0.86 * s), (0.66 * s, 0.46 * s)]
        outer += arc(half, 0.46 * s, 0.16 * s, 0, -math.pi, 32)
        outer += [(0.34 * s, 0.86 * s)]
        return [outer]

    if name == "cross":
        t = 0.17
        return [_poly([
            (0.5 - t, 0.10), (0.5 + t, 0.10), (0.5 + t, 0.5 - t), (0.90, 0.5 - t),
            (0.90, 0.5 + t), (0.5 + t, 0.5 + t), (0.5 + t, 0.90), (0.5 - t, 0.90),
            (0.5 - t, 0.5 + t), (0.10, 0.5 + t), (0.10, 0.5 - t), (0.5 - t, 0.5 - t),
        ], s)]

    if name == "slash":
        return [_poly([(0.56, 0.10), (0.88, 0.10), (0.44, 0.90), (0.12, 0.90)], s)]

    if name == "grid":
        r = s * 0.105
        out = []
        for gy in (0.28, 0.72):
            for gx in (0.28, 0.72):
                out.append(circle(gx * s, gy * s, r, 40))
        return out

    if name == "aperture":
        outer = circle(half, half, s * 0.40, 72)
        inner = circle(half, half, s * 0.20, 72)
        bar = rounded_rect(half - 0.03 * s, 0.05 * s, 0.06 * s, 0.40 * s, 0.03 * s)
        return [outer, inner[::-1], bar]

    raise ValueError(f"unknown shape {name!r}")


SHAPES = (
    "ring", "dot", "orbit", "hexagon", "triangle", "diamond",
    "chevron", "bars", "arch", "cross", "slash", "grid", "aperture",
)


# ==========================================================================
# SVG
# ==========================================================================


def contours_to_svg_path(contours: list[Contour], precision: int = 2) -> str:
    """Closed polygons as an SVG `d` attribute. fill-rule:nonzero matches the
    rasteriser, so the SVG and the PNGs agree on every hole."""
    parts = []
    for contour in contours:
        if len(contour) < 2:
            continue
        pts = ["M"]
        for i, (x, y) in enumerate(contour):
            if i == 1:
                pts.append("L")
            pts.append(f"{round(x, precision)} {round(y, precision)}")
        parts.append(" ".join(pts) + " Z")
    return " ".join(parts)
