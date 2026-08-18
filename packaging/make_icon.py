"""Build the official C-Lite feather icon set.

Source of truth: the Tk feather icon resources embedded in tk86t.dll
(the same icon Tk shows in the title bar).  This script decodes the
32-bit BMP entries, upscales the largest (64x64) to 128/256, and writes:

  icons/app.ico   - multi-resolution Windows icon (16/24/32/48/64 BMP
                    + 128/256 PNG entries)
  icons/app.png   - 256x256 PNG of the feather (runtime/iconphoto use)

Pure stdlib.  Run from the project root:
  python packaging/make_icon.py
"""

import os
import struct
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = r"C:\Users\nitin\AppData\Local\Programs\Python\Python313\DLLs\tk86t.dll"
OUT_DIR = os.path.join(ROOT, "icons")

PNG_SIZES = (128, 256)
BMP_SIZES = (16, 24, 32, 48, 64)

# ----------------------------------------------------------------------
#  read tk86t.dll icon resources
# ----------------------------------------------------------------------

def extract_from_dll(path):
    data = open(path, "rb").read()

    def u16(off):
        return struct.unpack_from("<H", data, off)[0]

    def u32(off):
        return struct.unpack_from("<I", data, off)[0]

    e = u32(0x3C)
    coff = e + 4
    opt = coff + 20
    magic = u16(opt)
    dd = opt + (96 if magic == 0x10B else 112)
    res_dir = u32(dd + 16)
    sec_off = opt + u16(coff + 16)
    secs = []
    for i in range(u16(coff + 2)):
        b = sec_off + i * 40
        secs.append((u32(b + 12), u32(b + 16), u32(b + 20)))

    def r2o(rva):
        for v, rw, rp in secs:
            if v <= rva < v + max(rw, 1):
                return rp + (rva - v)
        raise ValueError(hex(rva))

    def rd(rva, size):
        return data[r2o(rva):r2o(rva) + size]

    def dir_entries(rva):
        base = r2o(rva)
        cnt = u16(base + 12) + u16(base + 14)
        return [(u32(base + 16 + i * 8), u32(base + 16 + i * 8 + 4))
                for i in range(cnt)]

    def leaf(rva):
        out = {}
        for name, off in dir_entries(rva):
            if off & 0x80000000:
                sub = res_dir + (off & 0x7FFFFFFF)
                _, off2 = dir_entries(sub)[0]
                if off2 & 0x80000000:
                    lang = res_dir + (off2 & 0x7FFFFFFF)
                    _, off3 = dir_entries(lang)[0]
                    de = res_dir + off3
                else:
                    de = res_dir + off2
            else:
                de = res_dir + off
            doff, dsize = u32(r2o(de)), u32(r2o(de) + 4)
            out[name] = rd(doff, dsize)
        return out

    icons = groups = {}
    for name, off in dir_entries(res_dir):
        if off & 0x80000000:
            sub = res_dir + (off & 0x7FFFFFFF)
            if name == 3:
                icons = leaf(sub)
            elif name == 14:
                groups = leaf(sub)

    if not groups:
        raise RuntimeError("no icon group in %s" % path)
    gid, gdata = sorted(groups.items())[0]
    count = struct.unpack_from("<H", gdata, 4)[0]
    entries = {}
    for i in range(count):
        base = 6 + i * 14
        w, h, _, _, _, bitc, size, iconid = struct.unpack_from(
            "<BBBBHHIH", gdata, base)
        if bitc == 32:
            entries[w] = icons[iconid][:size]
    return entries


def decode_bmp_icon(raw):
    """Decode a 32-bit BMP icon image -> (width, height, rgba list top-down)."""
    w = struct.unpack_from("<i", raw, 4)[0]
    h = struct.unpack_from("<i", raw, 8)[0] // 2
    xor_size = w * h * 4
    xor = raw[40:40 + xor_size]
    pix = [[tuple(xor[(y * w + x) * 4:(y * w + x) * 4 + 4])
            for x in range(w)] for y in range(h)]
    return w, h, list(reversed(pix))

# ----------------------------------------------------------------------
#  scaling
# ----------------------------------------------------------------------

def scale(img, ow, oh, nw, nh):
    """Bilinear scale of a top-down RGBA list to nw x nh."""
    out = [[None] * nw for _ in range(nh)]
    for y in range(nh):
        fy = (y + 0.5) * oh / nh - 0.5
        y0 = max(0, int(fy))
        y1 = min(oh - 1, y0 + 1)
        ty = fy - y0
        for x in range(nw):
            fx = (x + 0.5) * ow / nw - 0.5
            x0 = max(0, int(fx))
            x1 = min(ow - 1, x0 + 1)
            tx = fx - x0
            p = [0, 0, 0, 0]
            for yy, wy in ((y0, 1 - ty), (y1, ty)):
                for xx, wx in ((x0, 1 - tx), (x1, tx)):
                    c = img[yy][xx]
                    wgt = wx * wy
                    for k in range(4):
                        p[k] += c[k] * wgt
            out[y][x] = tuple(max(0, min(255, int(round(v)))) for v in p)
    return out

# ----------------------------------------------------------------------
#  encoders
# ----------------------------------------------------------------------

def png_bytes(px, w, h):
    def chunk(t, d):
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(
            ">I", zlib.crc32(c) & 0xffffffff)
    raw = b"".join(b"\x00" + b"".join(bytes(py) for py in row) for row in px)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))

def bmp_icon_bytes(px, w, h):
    xor = bytearray()
    for y in range(h - 1, -1, -1):
        for x in range(w):
            b, g, r, a = px[y][x]
            xor += bytes((b, g, r, a))
    androw = ((w + 31) // 32) * 4
    andmask = bytearray()
    for y in range(h - 1, -1, -1):
        acc = 0
        n = 0
        for x in range(w):
            acc = (acc << 1) | (0 if px[y][x][3] >= 128 else 1)
            n += 1
            if n == 8:
                andmask.append(acc)
                acc, n = 0, 0
        if n:
            andmask.append(acc << (8 - n))
            nbytes = (n + 7) // 8
        else:
            nbytes = 0
        andmask += bytes(max(0, androw - nbytes))
    return struct.pack("<IiiHHIIIIII", 40, w, h * 2, 1, 32, 0,
                       len(xor) + len(andmask), 0, 0, 0, 0) + xor + andmask

def write_ico(path, bmp_images, png_images):
    total = len(bmp_images) + len(png_images)
    out = bytearray(struct.pack("<HHH", 0, 1, total))
    offset = 6 + 16 * total
    blobs = []
    for size, blob in sorted(bmp_images.items()):
        out += struct.pack("<BBBBHHII", size if size < 256 else 0,
                           size if size < 256 else 0, 0, 0, 1, 32,
                           len(blob), offset)
        offset += len(blob)
        blobs.append(blob)
    for size, blob in sorted(png_images.items()):
        out += struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32,
                           len(blob), offset)
        offset += len(blob)
        blobs.append(blob)
    for b in blobs:
        out += b
    open(path, "wb").write(bytes(out))

# ----------------------------------------------------------------------
#  main
# ----------------------------------------------------------------------

def main():
    src = os.environ.get("TK_DLL", SRC)
    if not os.path.isfile(src):
        sys.exit("tk86t.dll not found; set TK_DLL=path")
    raw = extract_from_dll(src)
    os.makedirs(OUT_DIR, exist_ok=True)

    bmp_images = {}
    big = None
    for size in BMP_SIZES:
        if size in raw:
            w, h, px = decode_bmp_icon(raw[size])
            bmp_images[size] = bytes(bmp_icon_bytes(px, w, h))
            big = (w, h, px)
    if big is None:
        sys.exit("no 32bpp icon found")

    png_images = {}
    for size in PNG_SIZES:
        w, h, px = big
        if size == w:
            scaled = px
        else:
            scaled = scale(px, w, h, size, size)
        png_images[size] = png_bytes(scaled, size, size)

    write_ico(os.path.join(OUT_DIR, "app.ico"), bmp_images, png_images)
    # 256 png for runtime iconphoto fallback
    open(os.path.join(OUT_DIR, "app.png"), "wb").write(
        png_images[256])
    print("wrote", os.path.join(OUT_DIR, "app.ico"),
          len(bmp_images), "bmp +", len(png_images), "png entries")
    print("wrote", os.path.join(OUT_DIR, "app.png"))
    print("bmp sizes:", sorted(bmp_images), "png sizes:", sorted(png_images))

if __name__ == "__main__":
    main()