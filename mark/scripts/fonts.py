"""TrueType parsing and glyph outline extraction, stdlib only.

Enough of the sfnt format to turn a string into filled contours: `cmap` for
character lookup, `glyf`/`loca` for outlines, `hmtx` for advances, `name` for
discovery. Handles simple and composite glyphs, and TrueType collections.

Not supported: CFF/PostScript outlines (most `.otf` files), which are a second
format entirely -- Type 2 charstrings rather than quadratic contours. Those get
a clear error naming the limitation, not a silent wrong result.
"""

from __future__ import annotations

import os
import struct
import sys

Point = tuple[float, float]
Contour = list[Point]


class FontError(ValueError):
    pass


# ==========================================================================
# Glyph flags
# ==========================================================================

ON_CURVE = 0x01
X_SHORT = 0x02
Y_SHORT = 0x04
REPEAT = 0x08
X_SAME = 0x10
Y_SAME = 0x20

ARG_1_AND_2_ARE_WORDS = 0x0001
ARGS_ARE_XY_VALUES = 0x0002
WE_HAVE_A_SCALE = 0x0008
MORE_COMPONENTS = 0x0020
WE_HAVE_AN_X_AND_Y_SCALE = 0x0040
WE_HAVE_A_TWO_BY_TWO = 0x0080


# ==========================================================================
# Font
# ==========================================================================


class Font:
    """A parsed TrueType face."""

    def __init__(self, data: bytes, index: int = 0, path: str = "<memory>"):
        self.data = data
        self.path = path
        self.tables = self._read_directory(index)

        if b"glyf" not in self.tables or b"loca" not in self.tables:
            if b"CFF " in self.tables or b"CFF2" in self.tables:
                raise FontError(
                    f"{os.path.basename(path)} uses CFF/PostScript outlines, which "
                    "this renderer does not read. Use the TrueType (.ttf) cut of "
                    "the family, or pass --image with a PNG of the mark."
                )
            raise FontError(f"{os.path.basename(path)} has no TrueType outlines")

        head = self._table(b"head")
        self.units_per_em = struct.unpack(">H", head[18:20])[0] or 1000
        self.index_to_loc = struct.unpack(">h", head[50:52])[0]

        maxp = self._table(b"maxp")
        self.num_glyphs = struct.unpack(">H", maxp[4:6])[0]

        hhea = self._table(b"hhea")
        self.ascent, self.descent, self.line_gap = struct.unpack(">hhh", hhea[4:10])
        self.num_h_metrics = struct.unpack(">H", hhea[34:36])[0]

        self._loca = self._read_loca()
        self._cmap = self._read_cmap()
        self._cache: dict[int, list[Contour]] = {}

        self.family = self._name(1) or os.path.splitext(os.path.basename(path))[0]
        self.subfamily = self._name(2) or "Regular"
        self.full_name = self._name(4) or f"{self.family} {self.subfamily}"
        self.weight_class = self._weight_class()

    # -- tables ----------------------------------------------------------

    def _read_directory(self, index: int) -> dict[bytes, tuple[int, int]]:
        data = self.data
        if len(data) < 12:
            raise FontError("file is too short to be a font")

        offset = 0
        if data[:4] == b"ttcf":
            count = struct.unpack(">I", data[8:12])[0]
            if index >= count:
                raise FontError(f"collection holds {count} fonts; index {index} is out of range")
            offset = struct.unpack(">I", data[12 + index * 4 : 16 + index * 4])[0]

        tag = data[offset : offset + 4]
        if tag not in (b"\x00\x01\x00\x00", b"true", b"ttcf", b"OTTO"):
            raise FontError("not a TrueType or OpenType font")

        (num_tables,) = struct.unpack(">H", data[offset + 4 : offset + 6])
        tables = {}
        pos = offset + 12
        for _ in range(num_tables):
            if pos + 16 > len(data):
                break
            name = data[pos : pos + 4]
            start, length = struct.unpack(">II", data[pos + 8 : pos + 16])
            tables[name] = (start, length)
            pos += 16
        return tables

    def _table(self, tag: bytes) -> bytes:
        if tag not in self.tables:
            raise FontError(f"font is missing the required `{tag.decode()}` table")
        start, length = self.tables[tag]
        return self.data[start : start + length]

    def _optional(self, tag: bytes) -> bytes | None:
        if tag not in self.tables:
            return None
        start, length = self.tables[tag]
        return self.data[start : start + length]

    def _read_loca(self) -> list[int]:
        raw = self._table(b"loca")
        n = self.num_glyphs + 1
        if self.index_to_loc == 0:
            vals = struct.unpack(f">{min(n, len(raw)//2)}H", raw[: min(n, len(raw) // 2) * 2])
            return [v * 2 for v in vals]
        return list(struct.unpack(f">{min(n, len(raw)//4)}I", raw[: min(n, len(raw) // 4) * 4]))

    # -- name ------------------------------------------------------------

    def _name(self, name_id: int) -> str | None:
        """Pick the English record. A font's name table is multilingual, and on
        a localised Windows the first Windows-platform record can be e.g.
        'Negreta' rather than 'Bold' -- which silently breaks style matching."""
        raw = self._optional(b"name")
        if not raw or len(raw) < 6:
            return None
        count, string_offset = struct.unpack(">HH", raw[2:6])

        best, best_score = None, -1
        for i in range(count):
            rec = 6 + i * 12
            if rec + 12 > len(raw):
                break
            platform, _encoding, lang, nid, length, offset = struct.unpack(
                ">HHHHHH", raw[rec : rec + 12]
            )
            if nid != name_id:
                continue
            chunk = raw[string_offset + offset : string_offset + offset + length]
            try:
                if platform in (0, 3):
                    text = chunk.decode("utf-16-be", "ignore")
                else:
                    text = chunk.decode("latin-1", "ignore")
            except Exception:
                continue
            text = text.strip("\x00").strip()
            if not text:
                continue

            if platform == 3 and lang == 0x0409:      # Windows, US English
                score = 5
            elif platform == 0:                        # Unicode, language-neutral
                score = 4
            elif platform == 1 and lang == 0:          # Mac, English
                score = 3
            elif platform == 3:
                score = 2
            else:
                score = 1
            if score > best_score:
                best, best_score = text, score
        return best

    def _weight_class(self) -> int:
        os2 = self._optional(b"OS/2")
        if os2 and len(os2) >= 6:
            wc = struct.unpack(">H", os2[4:6])[0]
            if 1 <= wc <= 1000:
                return wc
        return 700 if self.is_bold else 400

    @property
    def is_bold(self) -> bool:
        """From OS/2 fsSelection, falling back to head.macStyle. Both are
        numeric flags, so this works whatever language the name table is in."""
        os2 = self._optional(b"OS/2")
        if os2 and len(os2) >= 64:
            return bool(struct.unpack(">H", os2[62:64])[0] & 0x20)
        head = self._optional(b"head")
        if head and len(head) >= 46:
            return bool(struct.unpack(">H", head[44:46])[0] & 0x01)
        return False

    @property
    def is_italic(self) -> bool:
        os2 = self._optional(b"OS/2")
        if os2 and len(os2) >= 64:
            return bool(struct.unpack(">H", os2[62:64])[0] & 0x01)
        head = self._optional(b"head")
        if head and len(head) >= 46:
            return bool(struct.unpack(">H", head[44:46])[0] & 0x02)
        return False

    # -- cmap ------------------------------------------------------------

    def _read_cmap(self) -> dict[int, int]:
        raw = self._optional(b"cmap")
        if not raw:
            return {}
        (count,) = struct.unpack(">H", raw[2:4])

        best_offset, best_score = None, -1
        for i in range(count):
            rec = 4 + i * 8
            if rec + 8 > len(raw):
                break
            platform, encoding, offset = struct.unpack(">HHI", raw[rec : rec + 8])
            # Prefer full-Unicode subtables over BMP-only ones.
            score = {
                (3, 10): 5, (0, 4): 5, (0, 6): 5,
                (3, 1): 4, (0, 3): 4, (0, 2): 3, (0, 1): 3, (0, 0): 3,
                (1, 0): 1, (3, 0): 1,
            }.get((platform, encoding), 0)
            if score > best_score:
                best_score, best_offset = score, offset
        if best_offset is None or best_offset >= len(raw):
            return {}

        sub = raw[best_offset:]
        (fmt,) = struct.unpack(">H", sub[:2])
        if fmt == 4:
            return self._cmap4(sub)
        if fmt == 12:
            return self._cmap12(sub)
        if fmt == 6:
            first, count = struct.unpack(">HH", sub[6:10])
            ids = struct.unpack(f">{count}H", sub[10 : 10 + count * 2])
            return {first + i: g for i, g in enumerate(ids) if g}
        if fmt == 0:
            return {i: sub[6 + i] for i in range(min(256, len(sub) - 6)) if sub[6 + i]}
        return {}

    @staticmethod
    def _cmap4(sub: bytes) -> dict[int, int]:
        (seg_x2,) = struct.unpack(">H", sub[6:8])
        segs = seg_x2 // 2
        ends = struct.unpack(f">{segs}H", sub[14 : 14 + seg_x2])
        starts_at = 14 + seg_x2 + 2
        starts = struct.unpack(f">{segs}H", sub[starts_at : starts_at + seg_x2])
        deltas_at = starts_at + seg_x2
        deltas = struct.unpack(f">{segs}h", sub[deltas_at : deltas_at + seg_x2])
        ranges_at = deltas_at + seg_x2
        ranges = struct.unpack(f">{segs}H", sub[ranges_at : ranges_at + seg_x2])

        out: dict[int, int] = {}
        for i in range(segs):
            start, end = starts[i], ends[i]
            if start > end or end == 0xFFFF and start == 0xFFFF:
                continue
            for code in range(start, min(end, 0xFFFE) + 1):
                if ranges[i] == 0:
                    gid = (code + deltas[i]) & 0xFFFF
                else:
                    pos = ranges_at + i * 2 + ranges[i] + (code - start) * 2
                    if pos + 2 > len(sub):
                        continue
                    (gid,) = struct.unpack(">H", sub[pos : pos + 2])
                    if gid:
                        gid = (gid + deltas[i]) & 0xFFFF
                if gid:
                    out[code] = gid
        return out

    @staticmethod
    def _cmap12(sub: bytes) -> dict[int, int]:
        (ngroups,) = struct.unpack(">I", sub[12:16])
        out: dict[int, int] = {}
        for i in range(ngroups):
            pos = 16 + i * 12
            if pos + 12 > len(sub):
                break
            start, end, gid = struct.unpack(">III", sub[pos : pos + 12])
            if end - start > 0x10FFFF:
                continue
            for code in range(start, end + 1):
                out[code] = gid + (code - start)
        return out

    # -- metrics ---------------------------------------------------------

    def glyph_id(self, char: str) -> int:
        return self._cmap.get(ord(char), 0)

    def advance(self, gid: int) -> int:
        hmtx = self._table(b"hmtx")
        if self.num_h_metrics == 0:
            return self.units_per_em // 2
        i = min(gid, self.num_h_metrics - 1)
        pos = i * 4
        if pos + 2 > len(hmtx):
            return self.units_per_em // 2
        return struct.unpack(">H", hmtx[pos : pos + 2])[0]

    # -- outlines --------------------------------------------------------

    def glyph_contours(self, gid: int, depth: int = 0) -> list[Contour]:
        """Contours in font units, y-up, as the font stores them."""
        if gid in self._cache:
            return self._cache[gid]
        if depth > 5:
            raise FontError("composite glyph nested too deeply")
        if gid + 1 >= len(self._loca):
            return []

        start, end = self._loca[gid], self._loca[gid + 1]
        if end <= start:
            return []  # empty glyph, e.g. space

        glyf_start, _ = self.tables[b"glyf"]
        raw = self.data[glyf_start + start : glyf_start + end]
        if len(raw) < 10:
            return []

        (num_contours,) = struct.unpack(">h", raw[:2])
        result = (
            self._simple_glyph(raw, num_contours)
            if num_contours >= 0
            else self._composite_glyph(raw, depth)
        )
        if depth == 0:
            self._cache[gid] = result
        return result

    def _simple_glyph(self, raw: bytes, num_contours: int) -> list[Contour]:
        pos = 10
        end_pts = struct.unpack(f">{num_contours}H", raw[pos : pos + num_contours * 2])
        pos += num_contours * 2
        num_points = (end_pts[-1] + 1) if end_pts else 0
        if not num_points:
            return []

        (instr_len,) = struct.unpack(">H", raw[pos : pos + 2])
        pos += 2 + instr_len

        flags: list[int] = []
        while len(flags) < num_points and pos < len(raw):
            f = raw[pos]
            pos += 1
            flags.append(f)
            if f & REPEAT and pos < len(raw):
                repeat = raw[pos]
                pos += 1
                flags += [f] * repeat
        flags = flags[:num_points]
        if len(flags) < num_points:
            return []

        xs, x = [], 0
        for f in flags:
            if f & X_SHORT:
                if pos >= len(raw):
                    break
                d = raw[pos]
                pos += 1
                x += d if f & X_SAME else -d
            elif not f & X_SAME:
                if pos + 2 > len(raw):
                    break
                x += struct.unpack(">h", raw[pos : pos + 2])[0]
                pos += 2
            xs.append(x)

        ys, y = [], 0
        for f in flags:
            if f & Y_SHORT:
                if pos >= len(raw):
                    break
                d = raw[pos]
                pos += 1
                y += d if f & Y_SAME else -d
            elif not f & Y_SAME:
                if pos + 2 > len(raw):
                    break
                y += struct.unpack(">h", raw[pos : pos + 2])[0]
                pos += 2
            ys.append(y)

        if len(xs) < num_points or len(ys) < num_points:
            return []

        contours = []
        start = 0
        for end in end_pts:
            pts = [(float(xs[i]), float(ys[i]), bool(flags[i] & ON_CURVE))
                   for i in range(start, min(end + 1, num_points))]
            if len(pts) >= 2:
                contours.append(_quadratic_to_polyline(pts))
            start = end + 1
        return contours

    def _composite_glyph(self, raw: bytes, depth: int) -> list[Contour]:
        pos = 10
        out: list[Contour] = []
        while pos + 4 <= len(raw):
            flags, sub_gid = struct.unpack(">HH", raw[pos : pos + 4])
            pos += 4

            if flags & ARG_1_AND_2_ARE_WORDS:
                a1, a2 = struct.unpack(">hh", raw[pos : pos + 4])
                pos += 4
            else:
                a1, a2 = struct.unpack(">bb", raw[pos : pos + 2])
                pos += 2

            a, b, c, d = 1.0, 0.0, 0.0, 1.0
            if flags & WE_HAVE_A_SCALE:
                a = d = _f2dot14(raw, pos)
                pos += 2
            elif flags & WE_HAVE_AN_X_AND_Y_SCALE:
                a = _f2dot14(raw, pos)
                d = _f2dot14(raw, pos + 2)
                pos += 4
            elif flags & WE_HAVE_A_TWO_BY_TWO:
                a = _f2dot14(raw, pos)
                b = _f2dot14(raw, pos + 2)
                c = _f2dot14(raw, pos + 4)
                d = _f2dot14(raw, pos + 6)
                pos += 8

            dx, dy = (a1, a2) if flags & ARGS_ARE_XY_VALUES else (0, 0)
            for contour in self.glyph_contours(sub_gid, depth + 1):
                out.append([(a * x + c * y + dx, b * x + d * y + dy) for x, y in contour])

            if not flags & MORE_COMPONENTS:
                break
        return out


def _f2dot14(raw: bytes, pos: int) -> float:
    return struct.unpack(">h", raw[pos : pos + 2])[0] / 16384.0


def _quadratic_to_polyline(pts: list[tuple[float, float, bool]], steps: int = 8) -> Contour:
    """TrueType contours are quadratic B-splines: consecutive off-curve points
    imply an on-curve point at their midpoint."""
    n = len(pts)
    # Rotate so the contour starts on-curve, inserting a midpoint if need be.
    start = next((i for i, p in enumerate(pts) if p[2]), None)
    if start is None:
        x0, y0, _ = pts[0]
        xl, yl, _ = pts[-1]
        pts = [((x0 + xl) / 2, (y0 + yl) / 2, True)] + pts
        start = 0
        n += 1
    pts = pts[start:] + pts[:start]

    out: Contour = [(pts[0][0], pts[0][1])]
    i = 1
    while i <= n:
        cur = pts[i % n]
        if cur[2]:
            out.append((cur[0], cur[1]))
            i += 1
            continue

        nxt = pts[(i + 1) % n]
        if nxt[2]:
            end = (nxt[0], nxt[1])
            i += 2
        else:  # implied on-curve midpoint
            end = ((cur[0] + nxt[0]) / 2, (cur[1] + nxt[1]) / 2)
            i += 1

        p0 = out[-1]
        for s in range(1, steps + 1):
            t = s / steps
            u = 1 - t
            out.append(
                (
                    u * u * p0[0] + 2 * u * t * cur[0] + t * t * end[0],
                    u * u * p0[1] + 2 * u * t * cur[1] + t * t * end[1],
                )
            )
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return out


# ==========================================================================
# Text layout
# ==========================================================================


def layout(font: Font, text: str, size: float, tracking: float = 0.0):
    """Lay `text` out at `size` px. Returns (contours, width, height) in image
    space: y-down, origin at the top-left of the inked bounding box."""
    if not text:
        raise FontError("no text to render")

    scale = size / font.units_per_em
    track = tracking * size
    pen = 0.0
    raw: list[Contour] = []
    missing: list[str] = []

    for ch in text:
        gid = font.glyph_id(ch)
        if gid == 0 and not ch.isspace():
            missing.append(ch)
        for contour in font.glyph_contours(gid):
            raw.append([(pen + x * scale, -y * scale) for x, y in contour])
        pen += font.advance(gid) * scale + track

    if missing:
        raise FontError(
            f"{font.family} has no glyph for {' '.join(repr(c) for c in dict.fromkeys(missing))}"
        )
    if not raw:
        raise FontError(f"{text!r} rendered no outlines in {font.family}")

    xs = [p[0] for c in raw for p in c]
    ys = [p[1] for c in raw for p in c]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    shifted = [[(x - min_x, y - min_y) for x, y in c] for c in raw]
    return shifted, max_x - min_x, max_y - min_y


# ==========================================================================
# Discovery
# ==========================================================================


def font_dirs() -> list[str]:
    home = os.path.expanduser("~")
    if sys.platform == "win32":
        win = os.environ.get("SystemRoot", r"C:\Windows")
        local = os.environ.get("LOCALAPPDATA", os.path.join(home, "AppData", "Local"))
        dirs = [os.path.join(win, "Fonts"), os.path.join(local, "Microsoft", "Windows", "Fonts")]
    elif sys.platform == "darwin":
        dirs = ["/System/Library/Fonts", "/Library/Fonts", os.path.join(home, "Library", "Fonts")]
    else:
        dirs = [
            "/usr/share/fonts", "/usr/local/share/fonts",
            os.path.join(home, ".fonts"),
            os.path.join(home, ".local", "share", "fonts"),
        ]
    return [d for d in dirs if os.path.isdir(d)]


_EXTS = (".ttf", ".ttc", ".otf")

# Style names map to the same numeric axis OS/2 uses, so matching never depends
# on the language the name table happens to be written in.
WEIGHT_NAMES = {
    "thin": 100, "hairline": 100,
    "extralight": 200, "ultralight": 200,
    "light": 300,
    "regular": 400, "normal": 400, "book": 400, "roman": 400,
    "medium": 500,
    "semibold": 600, "demibold": 600,
    "bold": 700,
    "extrabold": 800, "ultrabold": 800,
    "black": 900, "heavy": 900,
}


class Face:
    """A discovered font file, described without fully parsing it."""

    __slots__ = ("family", "subfamily", "path", "weight", "italic", "index")

    def __init__(self, family, subfamily, path, weight, italic, index=0):
        self.family = family
        self.subfamily = subfamily
        self.path = path
        self.weight = weight
        self.italic = italic
        self.index = index

    def load(self) -> "Font":
        with open(self.path, "rb") as fh:
            return Font(fh.read(), index=self.index, path=self.path)

    def __repr__(self):
        return f"<Face {self.family} {self.subfamily} w={self.weight}>"


_scan_cache: list[Face] | None = None


def probe(path: str, index: int = 0) -> Face:
    """Read only the directory plus the `name` and `OS/2` tables.

    Scanning a font directory by reading every file whole costs seconds; most
    of those bytes are `glyf`, which listing never looks at.
    """
    with open(path, "rb") as fh:
        head = fh.read(12)
        offset = 0
        if head[:4] == b"ttcf":
            fh.seek(12 + index * 4)
            offset = struct.unpack(">I", fh.read(4))[0]
            fh.seek(offset)
            head = fh.read(12)
        if head[:4] not in (b"\x00\x01\x00\x00", b"true", b"OTTO"):
            raise FontError("not a TrueType or OpenType font")

        (num_tables,) = struct.unpack(">H", head[4:6])
        fh.seek(offset + 12)
        directory = fh.read(16 * num_tables)

        tables = {}
        for i in range(num_tables):
            rec = directory[i * 16 : i * 16 + 16]
            if len(rec) < 16:
                break
            tables[rec[:4]] = struct.unpack(">II", rec[8:16])

        if b"glyf" not in tables or b"loca" not in tables:
            raise FontError("no TrueType outlines")

        stub = {}
        for tag in (b"name", b"OS/2", b"head"):
            if tag in tables:
                start, length = tables[tag]
                fh.seek(start)
                stub[tag] = fh.read(min(length, 1 << 20))

    shim = _Stub(stub)
    family = Font._name(shim, 1) or os.path.splitext(os.path.basename(path))[0]
    subfamily = Font._name(shim, 2) or "Regular"
    italic = Font.is_italic.fget(shim)
    weight = Font._weight_class(shim)
    return Face(family, subfamily, path, weight, italic, index)


class _Stub:
    """Just enough of Font for the name/weight readers to run against a probe."""

    def __init__(self, tables: dict[bytes, bytes]):
        self._tables = tables

    def _optional(self, tag: bytes):
        return self._tables.get(tag)

    @property
    def is_bold(self) -> bool:
        return Font.is_bold.fget(self)


def scan_fonts(refresh: bool = False) -> list[Face]:
    """Every readable TrueType face on this machine."""
    global _scan_cache
    if _scan_cache is not None and not refresh:
        return _scan_cache

    found: list[Face] = []
    seen = set()
    for root in font_dirs():
        for dirpath, _dirnames, filenames in os.walk(root):
            for fn in sorted(filenames):
                if not fn.lower().endswith(_EXTS):
                    continue
                path = os.path.join(dirpath, fn)
                key = os.path.normcase(path)
                if key in seen:
                    continue
                seen.add(key)
                try:
                    found.append(probe(path))
                except (FontError, OSError, struct.error, IndexError, UnicodeError):
                    continue  # unreadable, or CFF -- simply not offered
    found.sort(key=lambda f: (f.family.lower(), f.italic, f.weight))
    _scan_cache = found
    return found


def _norm(s: str) -> str:
    return "".join(c for c in str(s).lower() if c.isalnum())


def resolve_weight(weight) -> int | None:
    """'bold' -> 700, '600' -> 600, None -> None."""
    if weight is None or weight == "":
        return None
    text = str(weight).strip()
    if text.isdigit():
        n = int(text)
        if not 1 <= n <= 1000:
            raise FontError(f"weight {n} is outside 1-1000")
        return n
    key = _norm(text)
    if key in WEIGHT_NAMES:
        return WEIGHT_NAMES[key]
    raise FontError(
        f"unknown weight {weight!r}; use a number (100-900) or one of: "
        + ", ".join(sorted(set(WEIGHT_NAMES)))
    )


def find_face(query: str, weight=None, italic: bool = False) -> Face:
    """Resolve a family name to the closest installed face."""
    target = _norm(query)
    if not target:
        raise FontError("no font named")

    faces = scan_fonts()
    exact = [f for f in faces if _norm(f.family) == target]
    prefix = [f for f in faces if _norm(f.family).startswith(target)]
    loose = [f for f in faces if target in _norm(f.family)]
    pool = exact or prefix or loose

    if not pool:
        stem = target[:4]
        near = sorted({f.family for f in faces if stem and stem in _norm(f.family)})
        hint = f" Closest installed: {', '.join(near[:6])}." if near else ""
        raise FontError(
            f"no font family matching {query!r} is installed on this machine.{hint} "
            "Run --list-fonts to see what is available, or pass a path to a .ttf file."
        )

    want = resolve_weight(weight)
    styled = [f for f in pool if f.italic == italic]
    if styled:
        pool = styled
    elif italic:
        raise FontError(
            f"{pool[0].family} is installed but has no italic cut "
            f"(found: {', '.join(sorted({f.subfamily for f in pool}))})."
        )

    if want is None:
        # No preference: the face nearest regular, not merely the first.
        return min(pool, key=lambda f: (abs(f.weight - 400), f.weight))
    return min(pool, key=lambda f: (abs(f.weight - want), f.weight))


def find_font(query: str, weight=None, italic: bool = False) -> Font:
    """Resolve a path or a family name to a loaded Font."""
    if os.path.isfile(query):
        with open(query, "rb") as fh:
            return Font(fh.read(), path=query)
    return find_face(query, weight, italic).load()
