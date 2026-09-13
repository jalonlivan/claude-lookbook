"""Image codecs, stdlib only.

Decodes PNG, GIF and BMP to straight RGBA8; encodes PNG and ICO. No Pillow,
no pip -- same constraint lookbook runs under.

JPEG is deliberately unsupported: it has no alpha channel and its ringing
artefacts sit right on the hard edges a logo is made of. The error says so and
names the fix.
"""

from __future__ import annotations

import struct
import zlib

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


class ImageError(ValueError):
    pass


# ==========================================================================
# Encode: PNG
# ==========================================================================


def encode_png(width: int, height: int, rgba: bytes) -> bytes:
    """RGBA8 bytes -> PNG. Filter 0 throughout: icons are mostly flat colour,
    so LZ77 matches whole identical rows and the filter earns nothing."""
    if len(rgba) != width * height * 4:
        raise ImageError(f"expected {width*height*4} bytes, got {len(rgba)}")

    stride = width * 4
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw += rgba[y * stride : (y + 1) * stride]

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        PNG_MAGIC
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


# ==========================================================================
# Encode: ICO
# ==========================================================================


def encode_ico(entries: list[tuple[int, bytes]]) -> bytes:
    """entries: [(size, png_bytes)]. PNG-compressed ICO entries, understood by
    every browser since IE11."""
    if not entries:
        raise ImageError("ICO needs at least one image")
    if len(entries) > 255:
        raise ImageError("ICO holds at most 255 images")

    head = struct.pack("<HHH", 0, 1, len(entries))
    offset = len(head) + 16 * len(entries)
    dirs, blobs = b"", b""
    for size, png in sorted(entries):
        if not 1 <= size <= 256:
            raise ImageError(f"ICO size {size} out of range")
        dirs += struct.pack(
            "<BBBBHHII",
            0 if size == 256 else size,  # 0 means 256
            0 if size == 256 else size,
            0,  # palette count
            0,  # reserved
            1,  # colour planes
            32,  # bits per pixel
            len(png),
            offset,
        )
        blobs += png
        offset += len(png)
    return head + dirs + blobs


# ==========================================================================
# Decode
# ==========================================================================


def decode_image(data: bytes) -> tuple[int, int, bytes]:
    """Sniff the magic bytes and decode. Returns (width, height, rgba8)."""
    if data[:8] == PNG_MAGIC:
        return decode_png(data)
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return decode_gif(data)
    if data[:2] == b"BM":
        return decode_bmp(data)
    if data[:3] == b"\xff\xd8\xff":
        raise ImageError(
            "JPEG has no alpha channel and its artefacts land on exactly the "
            "hard edges a logo is made of. Re-export the source as PNG."
        )
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        raise ImageError("WebP is not supported; re-export the source as PNG.")
    if data[:5] == b"<?xml" or data[:4] == b"<svg":
        raise ImageError(
            "SVG is vector, not raster. Rasterising it needs a full SVG engine. "
            "Export a PNG at 512x512 or larger and pass that."
        )
    raise ImageError("unrecognised image format (PNG, GIF and BMP are supported)")


# -- PNG -------------------------------------------------------------------

_CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}


def decode_png(data: bytes) -> tuple[int, int, bytes]:
    if data[:8] != PNG_MAGIC:
        raise ImageError("not a PNG")

    pos = 8
    width = height = depth = ctype = interlace = 0
    palette = b""
    trns = b""
    idat = bytearray()
    seen_ihdr = False

    while pos + 8 <= len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        tag = data[pos + 4 : pos + 8]
        body = data[pos + 8 : pos + 8 + length]
        if len(body) != length:
            raise ImageError("truncated PNG chunk")
        pos += 12 + length

        if tag == b"IHDR":
            width, height, depth, ctype, _comp, _filt, interlace = struct.unpack(
                ">IIBBBBB", body
            )
            seen_ihdr = True
        elif tag == b"PLTE":
            palette = body
        elif tag == b"tRNS":
            trns = body
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break

    if not seen_ihdr:
        raise ImageError("PNG has no IHDR")
    if interlace:
        raise ImageError(
            "interlaced (Adam7) PNG is not supported; re-save without interlacing"
        )
    if ctype not in _CHANNELS:
        raise ImageError(f"unsupported PNG colour type {ctype}")
    if depth not in (1, 2, 4, 8, 16):
        raise ImageError(f"unsupported PNG bit depth {depth}")
    if width <= 0 or height <= 0:
        raise ImageError("PNG has zero extent")

    channels = _CHANNELS[ctype]
    bits = depth * channels
    stride = (width * bits + 7) // 8
    bpp = max(1, bits // 8)

    raw = zlib.decompress(bytes(idat))
    if len(raw) < height * (stride + 1):
        raise ImageError("PNG image data is short")

    lines = _unfilter(raw, height, stride, bpp)
    samples = _expand(lines, width, height, depth, channels, stride)
    return width, height, _to_rgba(samples, width, height, ctype, depth, palette, trns)


def _unfilter(raw: bytes, height: int, stride: int, bpp: int) -> list[bytearray]:
    out = []
    prev = bytearray(stride)
    pos = 0
    for _ in range(height):
        ftype = raw[pos]
        line = bytearray(raw[pos + 1 : pos + 1 + stride])
        pos += 1 + stride

        if ftype == 0:
            pass
        elif ftype == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif ftype == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ftype == 3:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pred) & 0xFF
        else:
            raise ImageError(f"unknown PNG filter {ftype}")

        out.append(line)
        prev = line
    return out


def _expand(lines, width, height, depth, channels, stride) -> list[list[int]]:
    """Return one flat list of samples per row, normalised to 8-bit range."""
    rows = []
    if depth == 8:
        for line in lines:
            rows.append(list(line[: width * channels]))
    elif depth == 16:
        for line in lines:
            rows.append([line[i] for i in range(0, width * channels * 2, 2)])
    else:
        per_byte = 8 // depth
        mask = (1 << depth) - 1
        for line in lines:
            row = []
            need = width * channels
            for i in range(stride):
                byte = line[i]
                for k in range(per_byte):
                    if len(row) >= need:
                        break
                    shift = 8 - depth * (k + 1)
                    row.append((byte >> shift) & mask)
            rows.append(row)
    return rows


def _to_rgba(rows, width, height, ctype, depth, palette, trns) -> bytes:
    out = bytearray(width * height * 4)
    # sub-8-bit greyscale needs scaling to 0..255
    scale = 255 // ((1 << depth) - 1) if depth < 8 and ctype != 3 else 1
    i = 0
    for y in range(height):
        row = rows[y]
        for x in range(width):
            if ctype == 0:
                g = row[x] * scale
                r = gg = b = g
                a = 255
                if trns and len(trns) >= 2:
                    key = struct.unpack(">H", trns[:2])[0]
                    if depth == 16:
                        key >>= 8
                    if row[x] == key:
                        a = 0
                out[i : i + 4] = bytes((r, gg, b, a))
            elif ctype == 2:
                r, g, b = row[x * 3], row[x * 3 + 1], row[x * 3 + 2]
                a = 255
                if trns and len(trns) >= 6:
                    k = struct.unpack(">HHH", trns[:6])
                    if depth == 16:
                        k = tuple(v >> 8 for v in k)
                    if (r, g, b) == k:
                        a = 0
                out[i : i + 4] = bytes((r, g, b, a))
            elif ctype == 3:
                idx = row[x]
                if (idx + 1) * 3 > len(palette):
                    raise ImageError("PNG palette index out of range")
                r, g, b = palette[idx * 3 : idx * 3 + 3]
                a = trns[idx] if idx < len(trns) else 255
                out[i : i + 4] = bytes((r, g, b, a))
            elif ctype == 4:
                g = row[x * 2] * scale
                out[i : i + 4] = bytes((g, g, g, row[x * 2 + 1] * scale))
            else:  # 6
                out[i : i + 4] = bytes(row[x * 4 : x * 4 + 4])
            i += 4
    return bytes(out)


# -- GIF -------------------------------------------------------------------


def decode_gif(data: bytes) -> tuple[int, int, bytes]:
    """First frame only. A logo is not an animation."""
    pos = 6
    width, height, packed, _bg, _ar = struct.unpack("<HHBBB", data[pos : pos + 7])
    pos += 7

    gct = b""
    if packed & 0x80:
        n = 2 << (packed & 7)
        gct = data[pos : pos + n * 3]
        pos += n * 3

    transparent = -1
    while pos < len(data):
        block = data[pos]
        if block == 0x21:  # extension
            label = data[pos + 1]
            pos += 2
            if label == 0xF9:  # graphic control
                size = data[pos]
                flags = data[pos + 1]
                if flags & 1:
                    transparent = data[pos + 4]
                pos += size + 1
            while pos < len(data) and data[pos]:
                pos += data[pos] + 1
            pos += 1
        elif block == 0x2C:  # image descriptor
            ix, iy, iw, ih, ipacked = struct.unpack("<HHHHB", data[pos + 1 : pos + 10])
            pos += 10
            table = gct
            if ipacked & 0x80:
                n = 2 << (ipacked & 7)
                table = data[pos : pos + n * 3]
                pos += n * 3
            interlaced = bool(ipacked & 0x40)

            min_code = data[pos]
            pos += 1
            stream = bytearray()
            while pos < len(data) and data[pos]:
                size = data[pos]
                stream += data[pos + 1 : pos + 1 + size]
                pos += size + 1

            indices = _lzw(bytes(stream), min_code, iw * ih)
            if interlaced:
                indices = _deinterlace(indices, iw, ih)
            return width, height, _gif_rgba(
                indices, width, height, ix, iy, iw, ih, table, transparent
            )
        elif block == 0x3B:
            break
        else:
            pos += 1
    raise ImageError("GIF contains no image frame")


def _lzw(stream: bytes, min_code: int, expected: int) -> list[int]:
    clear = 1 << min_code
    end = clear + 1
    size = min_code + 1
    table = [[i] for i in range(clear)] + [[], []]
    out: list[int] = []
    prev = None
    bitpos = 0
    total = len(stream) * 8

    while bitpos + size <= total:
        byte, bit = bitpos >> 3, bitpos & 7
        chunk = int.from_bytes(stream[byte : byte + 3].ljust(3, b"\0"), "little")
        code = (chunk >> bit) & ((1 << size) - 1)
        bitpos += size

        if code == clear:
            table = [[i] for i in range(clear)] + [[], []]
            size = min_code + 1
            prev = None
            continue
        if code == end:
            break

        if code < len(table) and (code < clear or table[code]):
            entry = table[code]
        elif prev is not None:
            entry = prev + prev[:1]
        else:
            raise ImageError("corrupt GIF LZW stream")

        out += entry
        if prev is not None:
            table.append(prev + entry[:1])
            if len(table) >= (1 << size) and size < 12:
                size += 1
        prev = entry
        if len(out) >= expected:
            break
    return out


def _deinterlace(indices: list[int], w: int, h: int) -> list[int]:
    out = [0] * (w * h)
    src = 0
    for start, step in ((0, 8), (4, 8), (2, 4), (1, 2)):
        for y in range(start, h, step):
            out[y * w : y * w + w] = indices[src : src + w]
            src += w
    return out


def _gif_rgba(indices, width, height, ix, iy, iw, ih, table, transparent) -> bytes:
    out = bytearray(width * height * 4)  # zero-filled = transparent
    for y in range(ih):
        ty = iy + y
        if ty >= height:
            break
        for x in range(iw):
            tx = ix + x
            if tx >= width:
                break
            src = y * iw + x
            if src >= len(indices):
                break
            idx = indices[src]
            if idx == transparent:
                continue
            if (idx + 1) * 3 > len(table):
                continue
            o = (ty * width + tx) * 4
            out[o : o + 3] = table[idx * 3 : idx * 3 + 3]
            out[o + 3] = 255
    return bytes(out)


# -- BMP -------------------------------------------------------------------


def decode_bmp(data: bytes) -> tuple[int, int, bytes]:
    (data_offset,) = struct.unpack("<I", data[10:14])
    (header_size,) = struct.unpack("<I", data[14:18])
    if header_size < 40:
        raise ImageError("BMP core headers (OS/2) are not supported")

    width, height = struct.unpack("<ii", data[18:26])
    bits, compression = struct.unpack("<HI", data[28:34])
    if compression not in (0, 3):
        raise ImageError("compressed BMP is not supported")
    if bits not in (24, 32):
        raise ImageError(f"{bits}-bit BMP is not supported (needs 24 or 32)")

    top_down = height < 0
    height = abs(height)
    stride = ((width * bits + 31) // 32) * 4
    out = bytearray(width * height * 4)

    for row in range(height):
        y = row if top_down else height - 1 - row
        base = data_offset + row * stride
        for x in range(width):
            p = base + x * (bits // 8)
            if p + 2 >= len(data):
                raise ImageError("truncated BMP pixel data")
            b, g, r = data[p], data[p + 1], data[p + 2]
            a = data[p + 3] if bits == 32 else 255
            o = (y * width + x) * 4
            out[o : o + 4] = bytes((r, g, b, a))

    # A 32-bit BMP with an all-zero alpha channel means "no alpha", not "invisible".
    if bits == 32 and not any(out[3::4]):
        out[3::4] = b"\xff" * (width * height)
    return width, height, bytes(out)
