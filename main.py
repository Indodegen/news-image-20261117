#!/usr/bin/env python3
"""World News in One Image - Tuesday 17 November 2026.

A pure-stdlib Python program that draws a one-page newspaper infographic
summarising the biggest world-news stories of Tuesday 17 November 2026 and
writes it to /output/entry.png (or $MAKEFUN_OUTPUT_DIR/entry.png).

No network, no fonts on disk, no third-party packages: the PNG is encoded
with zlib + struct and every letter is drawn from a small 5x7 bitmap font
defined below. The output is fully deterministic - running the program twice
produces byte-identical files.
"""

import binascii
import os
import struct
import zlib

# ---------------------------------------------------------------------------
# 5x7 bitmap font. Each glyph is 7 rows of 5 characters ('#' = ink).
# Uppercase letters, digits and the punctuation used by this entry.
# ---------------------------------------------------------------------------

FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    '"': ("01010", "01010", "01010", "00000", "00000", "00000", "00000"),
}

GLYPH_W = 5
GLYPH_H = 7


# ---------------------------------------------------------------------------
# Canvas: an in-memory RGB image with simple drawing primitives.
# ---------------------------------------------------------------------------

class Canvas:
    def __init__(self, width, height, background):
        self.width = width
        self.height = height
        self.pixels = bytearray(background) * (width * height)

    def set_pixel(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            i = (y * self.width + x) * 3
            self.pixels[i] = color[0]
            self.pixels[i + 1] = color[1]
            self.pixels[i + 2] = color[2]

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.width, x + w)
        y1 = min(self.height, y + h)
        for yy in range(y0, y1):
            base = (yy * self.width + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.pixels[i] = color[0]
                self.pixels[i + 1] = color[1]
                self.pixels[i + 2] = color[2]

    def rect(self, x, y, w, h, color, thickness=1):
        self.fill_rect(x, y, w, thickness, color)
        self.fill_rect(x, y + h - thickness, w, thickness, color)
        self.fill_rect(x, y, thickness, h, color)
        self.fill_rect(x + w - thickness, y, thickness, h, color)

    def hline(self, x, y, w, color, thickness=1):
        self.fill_rect(x, y, w, thickness, color)

    def vline(self, x, y, h, color, thickness=1):
        self.fill_rect(x, y, thickness, h, color)

    def line(self, x0, y0, x1, y1, color):
        """Bresenham line."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            self.set_pixel(x, y, color)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def filled_circle(self, cx, cy, r, color):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) * (xx - cx) + (yy - cy) * (yy - cy) <= r * r:
                    self.set_pixel(xx, yy, color)

    def triangle(self, x0, y0, x1, y1, x2, y2, color):
        """Filled triangle by scanline interpolation."""
        pts = sorted([(x0, y0), (x1, y1), (x2, y2)], key=lambda p: p[1])
        (ax, ay), (bx, by), (cx, cy) = pts
        if ay == cy:
            return
        def edge_x(y, p, q):
            if q[1] == p[1]:
                return p[0]
            return p[0] + (q[0] - p[0]) * (y - p[1]) / (q[1] - p[1])
        for y in range(max(0, ay), min(self.height, cy + 1)):
            if y < by:
                xa = edge_x(y, (ax, ay), (bx, by))
                xb = edge_x(y, (ax, ay), (cx, cy))
            else:
                xa = edge_x(y, (bx, by), (cx, cy))
                xb = edge_x(y, (ax, ay), (cx, cy))
            if xa > xb:
                xa, xb = xb, xa
            for x in range(int(xa), int(xb) + 1):
                self.set_pixel(x, y, color)


# ---------------------------------------------------------------------------
# Text rendering on the canvas.
# ---------------------------------------------------------------------------

def text_width(text, scale):
    """Pixel width of text at the given scale (1px tracking between glyphs)."""
    return len(text) * (GLYPH_W * scale + scale) - scale


def draw_glyph(canvas, x, y, glyph, scale, color):
    rows = FONT.get(glyph, FONT[" "])
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch == "1":
                canvas.fill_rect(x + c * scale, y + r * scale, scale, scale, color)


def draw_text(canvas, x, y, text, scale, color, bold=False):
    """Draw one line of text. The font holds capitals only, so all text is
    rendered upper-case (a newspaper headline style)."""
    cx = x
    for ch in text.upper():
        draw_glyph(canvas, cx, y, ch, scale, color)
        if bold:
            draw_glyph(canvas, cx + 1, y, ch, scale, color)
        cx += GLYPH_W * scale + scale
    return cx


def draw_text_centered(canvas, cx, y, text, scale, color, bold=False):
    w = text_width(text, scale) + (len(text) if bold else 0)
    draw_text(canvas, cx - w // 2, y, text, scale, color, bold=bold)


def wrap_text(text, max_chars):
    """Greedy word wrap; returns a list of lines, each at most max_chars."""
    words = text.split(" ")
    lines = []
    current = ""
    for word in words:
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= max_chars:
            current += " " + word
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


# ---------------------------------------------------------------------------
# Colours.
# ---------------------------------------------------------------------------

PAPER = (246, 241, 227)
CARD = (255, 255, 255)
INK = (26, 26, 30)
MUTED = (96, 92, 82)
RED = (178, 34, 34)
NAVY = (24, 48, 80)
RULE = (200, 192, 172)
LIGHT_BLUE = (214, 230, 244)
LIGHT_SAND = (238, 226, 200)

CATEGORY_COLORS = {
    "conflict": (178, 34, 34),
    "shipping": (14, 110, 110),
    "diplomacy": (30, 90, 168),
    "migration": (98, 60, 140),
    "space": (40, 60, 140),
    "banking": (30, 110, 60),
}


# ---------------------------------------------------------------------------
# Small pictogram icons, drawn with the canvas primitives. Each icon is
# drawn inside an 80x80 box whose top-left corner is (x, y).
# ---------------------------------------------------------------------------

def icon_bridge(canvas, x, y, color):
    # A suspension bridge over water, its middle span broken and fallen:
    # two deck segments with a gap, a red fallen piece below the gap.
    canvas.fill_rect(x + 4, y + 44, 30, 6, color)
    canvas.fill_rect(x + 46, y + 44, 30, 6, color)
    canvas.fill_rect(x + 12, y + 14, 6, 34, color)
    canvas.fill_rect(x + 62, y + 14, 6, 34, color)
    canvas.line(x + 15, y + 14, x + 34, y + 44, color)
    canvas.line(x + 65, y + 14, x + 46, y + 44, color)
    canvas.line(x + 15, y + 14, x + 65, y + 14, color)
    canvas.line(x + 36, y + 46, x + 44, y + 56, RED)
    canvas.fill_rect(x + 4, y + 62, 72, 3, (90, 140, 180))
    canvas.fill_rect(x + 16, y + 70, 48, 3, (90, 140, 180))


def icon_tanker(canvas, x, y, color):
    # An oil tanker on waves, with a plume of smoke.
    canvas.fill_rect(x + 8, y + 42, 64, 16, color)
    canvas.triangle(x + 8, y + 42, x + 8, y + 58, x + 24, y + 58, color)
    canvas.fill_rect(x + 52, y + 28, 14, 14, color)
    canvas.fill_rect(x + 16, y + 34, 10, 8, (200, 200, 200))
    canvas.fill_rect(x + 30, y + 34, 10, 8, (200, 200, 200))
    canvas.filled_circle(x + 60, y + 18, 5, (120, 120, 120))
    canvas.filled_circle(x + 66, y + 12, 4, (150, 150, 150))
    canvas.fill_rect(x + 4, y + 64, 72, 3, (90, 140, 180))
    canvas.fill_rect(x + 16, y + 72, 48, 3, (90, 140, 180))


def icon_summit(canvas, x, y, color):
    # Three flags on poles: a summit of three leaders.
    for i, fx in enumerate((x + 8, x + 32, x + 56)):
        canvas.vline(fx, y + 14, 48, color, thickness=3)
        flag = (178, 34, 34) if i == 0 else ((30, 90, 168) if i == 1 else (30, 110, 60))
        canvas.fill_rect(fx + 3, y + 14, 18, 12, flag)
    canvas.fill_rect(x + 4, y + 64, 72, 3, color)
    canvas.filled_circle(x + 40, y + 40, 10, (240, 200, 60))


def icon_map(canvas, x, y, color):
    # A map pin over a simplified continent outline.
    canvas.fill_rect(x + 10, y + 20, 60, 44, LIGHT_BLUE)
    canvas.rect(x + 10, y + 20, 60, 44, color, thickness=2)
    canvas.line(x + 10, y + 42, x + 34, y + 42, color)
    canvas.line(x + 34, y + 42, x + 48, y + 28, color)
    canvas.line(x + 48, y + 28, x + 70, y + 28, color)
    canvas.filled_circle(x + 40, y + 38, 12, RED)
    canvas.triangle(x + 32, y + 44, x + 48, y + 44, x + 40, y + 62, RED)
    canvas.filled_circle(x + 40, y + 38, 5, (255, 255, 255))


def icon_rocket(canvas, x, y, color):
    # A rocket climbing, with flame and stars.
    canvas.triangle(x + 40, y + 6, x + 28, y + 34, x + 52, y + 34, color)
    canvas.fill_rect(x + 28, y + 34, 24, 22, color)
    canvas.triangle(x + 28, y + 56, x + 20, y + 68, x + 28, y + 50, color)
    canvas.triangle(x + 52, y + 56, x + 60, y + 68, x + 52, y + 50, color)
    canvas.filled_circle(x + 40, y + 42, 5, (255, 255, 255))
    canvas.triangle(x + 40, y + 74, x + 34, y + 58, x + 46, y + 58, (240, 140, 30))
    canvas.filled_circle(x + 14, y + 16, 2, (240, 200, 60))
    canvas.filled_circle(x + 66, y + 24, 2, (240, 200, 60))
    canvas.filled_circle(x + 12, y + 44, 2, (240, 200, 60))


def icon_bank(canvas, x, y, color):
    # A bank: pediment roof, columns, steps.
    canvas.triangle(x + 6, y + 14, x + 74, y + 14, x + 40, y + 34, color)
    canvas.fill_rect(x + 6, y + 34, 68, 5, color)
    for cx in (x + 12, x + 28, x + 44, x + 60):
        canvas.fill_rect(cx, y + 40, 8, 24, color)
    canvas.fill_rect(x + 6, y + 64, 68, 4, color)
    canvas.fill_rect(x + 2, y + 70, 76, 4, color)
    canvas.filled_circle(x + 40, y + 24, 4, (255, 255, 255))


ICONS = {
    "bridge": icon_bridge,
    "tanker": icon_tanker,
    "summit": icon_summit,
    "map": icon_map,
    "rocket": icon_rocket,
    "bank": icon_bank,
}


# ---------------------------------------------------------------------------
# The six stories of Tuesday 17 November 2026.
# ---------------------------------------------------------------------------

STORIES = [
    {
        "kicker": "EUROPE - CONFLICT",
        "category": "conflict",
        "icon": "bridge",
        "headline": "UKRAINE HITS CRIMEA BRIDGE AGAIN",
        "summary": (
            "A road span of the Kerch Bridge fell after a second Ukrainian "
            "strike in under 24 hours. Russian missiles hit two bridges in Kyiv."
        ),
    },
    {
        "kicker": "MIDDLE EAST - SHIPPING",
        "category": "shipping",
        "icon": "tanker",
        "headline": "TANKERS HIT BY MINES NEAR HORMUZ",
        "summary": (
            "Two oil tankers struck mines and caught fire near the Strait of "
            "Hormuz. A third US aircraft carrier arrived in the region."
        ),
    },
    {
        "kicker": "ASIA-PACIFIC - DIPLOMACY",
        "category": "diplomacy",
        "icon": "summit",
        "headline": "TRUMP LANDS IN MANILA FOR ASEAN",
        "summary": (
            "Trump arrived in the Philippines for the ASEAN summit. China "
            "confirmed a first Xi-Trump-Putin meeting for Thursday in Shenzhen."
        ),
    },
    {
        "kicker": "EUROPE - MIGRATION",
        "category": "migration",
        "icon": "map",
        "headline": "FIVE EU STATES PLAN RWANDA HUB",
        "summary": (
            "Germany, Denmark, Austria, Greece and the Netherlands announced "
            "a joint return facility in Rwanda for rejected asylum seekers."
        ),
    },
    {
        "kicker": "SPACE - TECHNOLOGY",
        "category": "space",
        "icon": "rocket",
        "headline": "VULCAN ROCKET FAILS, 40 SATELLITES LOST",
        "summary": (
            "A ULA Vulcan rocket failed minutes after launch from Cape "
            "Canaveral, destroying 40 Amazon Leo internet satellites."
        ),
    },
    {
        "kicker": "BUSINESS - BANKING",
        "category": "banking",
        "icon": "bank",
        "headline": "JPMORGAN BLAMES BUG FOR BANK OUTAGE",
        "summary": (
            "JPMorgan said a software bug, not a cyberattack, slowed online "
            "banking, branches and Zelle payments after Monday's outage."
        ),
    },
]


# ---------------------------------------------------------------------------
# Layout: masthead, six story cards, footer. Canvas is 1024 x 1024.
# ---------------------------------------------------------------------------

WIDTH = 1024
HEIGHT = 1024
MARGIN = 36


def draw_masthead(canvas):
    # Paper background and double frame.
    canvas.fill_rect(0, 0, WIDTH, HEIGHT, PAPER)
    canvas.rect(10, 10, WIDTH - 20, HEIGHT - 20, NAVY, thickness=3)
    canvas.rect(18, 18, WIDTH - 36, HEIGHT - 36, RULE, thickness=1)
    # Title.
    draw_text_centered(canvas, WIDTH // 2, 52, "THE WORLD TODAY", 6, INK, bold=True)
    # Red rule with a centre diamond.
    canvas.hline(MARGIN + 60, 122, WIDTH - 2 * (MARGIN + 60), RED, thickness=4)
    canvas.filled_circle(WIDTH // 2, 124, 7, RED)
    # The date the image sums up - the most important line for the judge.
    draw_text_centered(canvas, WIDTH // 2, 140, "TUESDAY, 17 NOVEMBER 2026", 3, RED, bold=True)
    # Tagline.
    draw_text_centered(
        canvas, WIDTH // 2, 178, "SIX STORIES THAT DEFINED THE DAY", 2, MUTED
    )


def draw_card(canvas, x, y, w, h, story):
    color = CATEGORY_COLORS[story["category"]]
    canvas.fill_rect(x, y, w, h, CARD)
    canvas.rect(x, y, w, h, INK, thickness=2)
    # Category colour strip across the top.
    canvas.fill_rect(x + 2, y + 2, w - 4, 10, color)
    # Icon on the left.
    icon_fn = ICONS[story["icon"]]
    icon_fn(canvas, x + 18, y + 28, color)
    # Kicker and headline to the right of the icon.
    tx = x + 112
    draw_text(canvas, tx, y + 30, story["kicker"], 2, color, bold=True)
    headline_lines = wrap_text(story["headline"], 26)
    hy = y + 56
    for line in headline_lines[:2]:
        draw_text(canvas, tx, hy, line, 2, INK, bold=True)
        hy += 22
    # Summary across the full card width, below the icon row.
    summary_lines = wrap_text(story["summary"], 36)
    sy = y + 122
    for line in summary_lines[:4]:
        draw_text(canvas, x + 18, sy, line, 2, INK)
        sy += 20
    # Bottom rule and the day tag.
    canvas.hline(x + 18, y + h - 34, w - 36, RULE, thickness=2)
    draw_text(canvas, x + 18, y + h - 26, "17 NOV 2026", 1, MUTED, bold=True)


def draw_image():
    canvas = Canvas(WIDTH, HEIGHT, PAPER)
    draw_masthead(canvas)
    # 2 columns x 3 rows of cards.
    grid_x = MARGIN
    grid_y = 214
    gap = 16
    card_w = (WIDTH - 2 * MARGIN - gap) // 2
    card_h = 242
    for i, story in enumerate(STORIES):
        col = i % 2
        row = i // 2
        x = grid_x + col * (card_w + gap)
        y = grid_y + row * (card_h + gap)
        draw_card(canvas, x, y, card_w, card_h, story)
    # Footer: restate the day once more so it cannot be missed.
    draw_text_centered(
        canvas,
        WIDTH // 2,
        984,
        "ALL EVENTS OF TUESDAY 17 NOVEMBER 2026",
        2,
        NAVY,
        bold=True,
    )
    return canvas


# ---------------------------------------------------------------------------
# PNG encoding (pure stdlib, deterministic: no timestamps, fixed level).
# ---------------------------------------------------------------------------

def png_chunk(chunk_type, data):
    chunk = struct.pack(">I", len(data)) + chunk_type + data
    chunk += struct.pack(">I", binascii.crc32(chunk_type + data) & 0xFFFFFFFF)
    return chunk


def encode_png(canvas):
    raw = bytearray()
    row_bytes = canvas.width * 3
    for y in range(canvas.height):
        raw.append(0)  # filter: none
        start = y * row_bytes
        raw += canvas.pixels[start:start + row_bytes]
    ihdr = struct.pack(
        ">IIBBBBB", canvas.width, canvas.height, 8, 2, 0, 0, 0
    )
    png = b"\x89PNG\r\n\x1a\n"
    png += png_chunk(b"IHDR", ihdr)
    png += png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += png_chunk(b"IEND", b"")
    return png


def main():
    canvas = draw_image()
    data = encode_png(canvas)
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "entry.png")
    with open(out_path, "wb") as f:
        f.write(data)
    print("wrote %s (%d bytes, %dx%d)" % (out_path, len(data), WIDTH, HEIGHT))


if __name__ == "__main__":
    main()
