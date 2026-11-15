"""Erzeugt assets/icon.ico fuer R3E Karriere in reinem Python (nur zlib).

Design: abgerundetes dunkles Quadrat (App-Dark #131318 mit feiner
Randlinie), diagonales RaceRoom-rotes Geschwindigkeitsband mit dunkler
Schattenlinie (45 Grad, #e8212b / #8f151c), darueber ein weisses K
(dunkle Kontur). Ausgabe: ICO mit PNG-Eintraegen in 16/24/32/48/64/128/256
px (Vista+-Format) plus Vorschau icon_256.png."""
import os
import struct
import zlib

MASTER = 1024

BG = (0x13, 0x13, 0x18)
EDGE = (0x2a, 0x2a, 0x33)
RED = (0xe8, 0x21, 0x2b)
RED_D = (0x8f, 0x15, 0x1c)
WHITE = (0xf4, 0xf4, 0xf6)

# K als Polygone, normiert (0..1)
K_POLYS = [
    [(0.255, 0.16), (0.415, 0.16), (0.415, 0.84), (0.255, 0.84)],
    [(0.435, 0.455), (0.505, 0.455), (0.755, 0.16), (0.625, 0.16)],
    [(0.435, 0.545), (0.505, 0.545), (0.755, 0.84), (0.625, 0.84)],
]


def _row_spans(polys, y):
    """Even-odd-Spans aller Polygone bei normierter Hoehe y."""
    xs = []
    for poly in polys:
        n = len(poly)
        for k in range(n):
            x1, y1 = poly[k]
            x2, y2 = poly[(k + 1) % n]
            if (y1 <= y < y2) or (y2 <= y < y1):
                xs.append(x1 + (x2 - x1) * (y - y1) / (y2 - y1))
    xs.sort()
    return [(xs[i], xs[i + 1]) for i in range(0, len(xs) - 1, 2)]


def _k_cover(res):
    """K-Deckung als Liste von Zeilen-Spans (Index = Zeile, res Pixel)."""
    return [_row_spans(K_POLYS, (y + 0.5) / res) for y in range(res)]


def render_master():
    n = MASTER
    r_corner = 0.16 * n
    band_c = 0.505 * n * 1.4142      # (x+y)-Schwerpunkt des Bands
    band_w = 0.16 * n * 1.4142
    edge_t = 0.012 * n
    kc = _k_cover(n)
    kexp = _k_cover(n)  # Kontur: wird unten per Aufweitung gezeichnet
    buf = bytearray(n * n * 3)
    i = 0
    for y in range(n):
        ky = (y + 0.5) / n
        kspans = kc[y]
        in_corner_row = not (r_corner <= y <= n - r_corner)
        diag_y = y
        for x in range(n):
            # abgerundetes Quadrat
            if in_corner_row and not (r_corner <= x <= n - r_corner):
                dx = min(max(x - r_corner, 0.0), r_corner) + r_corner
                # Punkt-zu-Eckzentrum-Abstand
                ex = r_corner if x < r_corner else n - r_corner
                ey = r_corner if y < r_corner else n - r_corner
                if (x - ex) ** 2 + (y - ey) ** 2 > r_corner * r_corner:
                    continue
            if (x < edge_t or y < edge_t
                    or x >= n - edge_t or y >= n - edge_t):
                col = EDGE
            else:
                col = BG
            # rotes Band mit Schattenlinie
            d = (x + diag_y) - band_c
            if -band_w <= d <= band_w:
                col = RED
            elif band_w < d <= band_w * 1.18:
                col = RED_D
            # K: Kontur (aufgeweitet), dann weisse Flaeche
            kx = (x + 0.5) / n
            hit = False
            for a, b in kspans:
                if a - 0.014 <= kx <= b + 0.014:
                    hit = True
                    break
                if kx < a:
                    break
            if hit:
                col = WHITE
                for a, b in kspans:
                    if a <= kx <= b:
                        break
                    if kx < a:
                        col = (0x0a, 0x0a, 0x0e)
                        break
                else:
                    col = (0x0a, 0x0a, 0x0e)
            buf[i] = col[0]
            buf[i + 1] = col[1]
            buf[i + 2] = col[2]
            i += 3
    return buf


def downsample(buf, size):
    n = MASTER
    step = n / size
    rows = []
    for ty in range(size):
        y0 = int(ty * step)
        y1 = max(y0 + 1, int((ty + 1) * step))
        row = bytearray()
        for tx in range(size):
            x0 = int(tx * step)
            x1 = max(x0 + 1, int((tx + 1) * step))
            r = g = b = 0
            cnt = 0
            for y in range(y0, y1):
                base = y * n * 3
                for x in range(x0, x1):
                    j = base + x * 3
                    r += buf[j]
                    g += buf[j + 1]
                    b += buf[j + 2]
                    cnt += 1
            row += bytes((r // cnt, g // cnt, b // cnt, 255))
        rows.append(bytes(row))
    return rows


def png_encode(rows, size):
    raw = b"".join(b"\x00" + r for r in rows)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def ico_encode(images):
    out = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    body = b""
    for size, data in images:
        w = 0 if size >= 256 else size
        out += struct.pack("<BBBBHHII", w, w, 0, 0, 1, 32, len(data), offset)
        body += data
        offset += len(data)
    return out + body


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    assets = os.path.normpath(os.path.join(here, "..", "assets"))
    os.makedirs(assets, exist_ok=True)
    buf = render_master()
    images = []
    for size in (16, 24, 32, 48, 64, 128, 256):
        data = png_encode(downsample(buf, size), size)
        images.append((size, data))
        print("gerendert:", size, len(data), "Bytes")
    with open(os.path.join(assets, "icon.ico"), "wb") as f:
        f.write(ico_encode(images))
    with open(os.path.join(assets, "icon_256.png"), "wb") as f:
        f.write(images[-1][1])
    print("OK -> assets/icon.ico",
          os.path.getsize(os.path.join(assets, "icon.ico")), "Bytes")


if __name__ == "__main__":
    main()
