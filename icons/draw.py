"""16x16 Yoto display icons, one per show. Transparent background, no black."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

P = {
    '.': None,
    'w': (255, 255, 255), 'y': (255, 214, 0), 'Y': (210, 150, 0), 'o': (255, 140, 0),
    'r': (235, 40, 40), 'p': (255, 110, 180), 'b': (40, 120, 255), 'c': (0, 200, 230),
    'g': (60, 210, 90), 's': (175, 180, 200), 'S': (110, 115, 140), 'm': (190, 70, 255),
    'n': (40, 60, 200),
}

ICONS = {
    # Friday Night Comedy: laughing face with happy tears
    'friday-night-comedy': """
.....yyyyyy.....
...yyyyyyyyyy...
..yyyyyyyyyyyy..
.yyyyyyyyyyyyyy.
.yyyyryyyyryyyy.
yyyryryyyyryryyy
cyyyyyyyyyyyyyyc
cyyyyyyyyyyyyyyc
yyyrrrrrrrrrryyy
yyyrwwwwwwwwryyy
.yyrrrrrrrrrryy.
.yyyrrpppprryyy.
..yyyrrrrrryyy..
...yyyyyyyyyy...
.....yyyyyy.....
................""",
    # Strong Message Here: megaphone with sound waves
    'strong-message-here': """
................
................
..........r.....
........rrr..r..
......rrrrr...r.
....rrrrrrr.r..r
.rrrrrrrrrr..r.r
.rwrrrrrrrr..r.r
.rwrrrrrrrr..r.r
.rrrrrrrrrr..r.r
....rrrrrrr.r..r
......rrrrr...r.
.....S..rrr..r..
.....S....r.....
................
................""",
    # The Bugle: brass bugle with a note
    'the-bugle': """
................
................
....yyyyyyyy....
...y........y...
..y..........y..
..y.........YYY.
..y........YYYY.
yyyyyyyyyyYYYYY.
...........YYYY.
............YYY.
...y.......y....
....yyyyyyy.....
................
................
................
................""",
    # No Such Thing As A Fish: orange fish with bubbles
    'no-such-thing-as-a-fish': """
................
............c...
..............c.
.............c..
.....oooooo.....
...oooooooooo..o
..oowoooyooooooo
.ooonwooyoooooo.
.ooooooooyooooo.
..oooooooyoooooo
...oooooooooo..o
.....oooooo.....
.......oo.......
................
................
................""",
    # Private Eye: a big watchful eye
    'private-eye': """
................
................
................
.....wwwwww.....
...ww......ww...
..w...bbbb...w..
.w...bbnnbb...w.
w....bnnnnb....w
w....bnnwnb....w
.w...bbnnbb...w.
..w...bbbb...w..
...ww......ww...
.....wwwwww.....
................
................
................""",
    # The Rest Is Politics: US: stars and stripes
    'the-rest-is-politics-us': """
................
................
................
bbbbbbbrrrrrrrrr
bwbwbwbwwwwwwwww
bbbbbbbrrrrrrrrr
bwbwbwbwwwwwwwww
bbbbbbbrrrrrrrrr
rrrrrrrrrrrrrrrr
wwwwwwwwwwwwwwww
rrrrrrrrrrrrrrrr
wwwwwwwwwwwwwwww
rrrrrrrrrrrrrrrr
.S..............
.S..............
.S..............""",
}

out = Path(sys.argv[1] if len(sys.argv) > 1 else '.')
SCALE = 16
sheet = Image.new('RGB', (len(ICONS) * (16 * SCALE + 20) + 20, 16 * SCALE + 40), (25, 25, 30))
for n, (name, art) in enumerate(ICONS.items()):
    rows = art.strip('\n').split('\n')
    assert len(rows) == 16 and all(len(r) == 16 for r in rows), (name, [len(r) for r in rows])
    img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if P[ch]:
                img.putpixel((x, y), P[ch] + (255,))
    img.save(out / f'{name}.png')
    # preview: big pixels as round "LEDs" on a dark panel, like the player
    d = ImageDraw.Draw(sheet)
    ox = 20 + n * (16 * SCALE + 20)
    for y in range(16):
        for x in range(16):
            px = img.getpixel((x, y))
            col = px[:3] if px[3] else (45, 45, 52)
            d.rounded_rectangle([ox + x * SCALE + 1, 20 + y * SCALE + 1,
                                 ox + (x + 1) * SCALE - 2, 20 + (y + 1) * SCALE - 2], 3, fill=col)
sheet.save(out / 'preview.png')
print('ok')
