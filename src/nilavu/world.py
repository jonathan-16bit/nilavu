"""Generate a small open woodland independently of source-file structure."""

from collections import deque
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import random

from nilavu.cells import line_width, visible_cells
from nilavu.navigation import LightPosition

WORLD_WIDTH = 120
WORLD_HEIGHT = 40


class Terrain(Enum):
    MOSS = "moss"
    GRASS = "grass"
    EARTH = "earth"
    CANOPY = "canopy"
    TRUNK = "trunk"
    WATER = "water"
    FLOWER = "flower"


BLOCKED = frozenset((Terrain.TRUNK, Terrain.WATER))


@dataclass(frozen=True)
class World:
    """An immutable cell map, fixed for the lifetime of an exploration run."""

    terrain: tuple[tuple[Terrain, ...], ...]
    lines: tuple[str, ...]
    spawn: tuple[int, int]
    pond: tuple[int, int]

    @property
    def width(self) -> int:
        return len(self.terrain[0])

    @property
    def height(self) -> int:
        return len(self.terrain)

    @property
    def text(self) -> str:
        return "\n".join(self.lines)

    def passable(self, x: int, y: int) -> bool:
        return (0 <= x < self.width and 0 <= y < self.height
                and self.terrain[y][x] not in BLOCKED)

    def starting_light(self) -> LightPosition:
        return LightPosition(self.width - 1, self.height - 1, *self.spawn)


def _ellipse(cx: int, cy: int, rx: int, ry: int) -> Iterator[tuple[int, int]]:
    """Yield clipped cell coordinates, using wider shapes for tall terminal cells."""
    for y in range(max(0, cy - ry), min(WORLD_HEIGHT, cy + ry + 1)):
        for x in range(max(0, cx - rx), min(WORLD_WIDTH, cx + rx + 1)):
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1:
                yield x, y


def _reachable(terrain: list[list[Terrain]], spawn: tuple[int, int]) -> set[tuple[int, int]]:
    reached = {spawn}
    queue = deque([spawn])
    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if (0 <= nx < WORLD_WIDTH and 0 <= ny < WORLD_HEIGHT
                    and terrain[ny][nx] not in BLOCKED and (nx, ny) not in reached):
                reached.add((nx, ny))
                queue.append((nx, ny))
    return reached


def _text_rows(source_text: str, terrain: list[list[Terrain]],
               rng: random.Random) -> tuple[str, ...]:
    """Arrange source glyphs along terrain shapes, rather than scattering words."""
    # Density describes scenery, not obstacles. Sparse ground leaves breathing
    # room, dense leaves reveal canopy outlines, and water has broken ripple rows.
    density = {Terrain.MOSS: 0.08, Terrain.GRASS: 0.20, Terrain.EARTH: 0.03,
               Terrain.CANOPY: 0.72, Terrain.TRUNK: 1.0, Terrain.FLOWER: 1.0}
    paint = [[((y % 2 == 0 and (x + y) % 3 != 0) if kind == Terrain.WATER
               else rng.random() < density[kind])
              for x, kind in enumerate(row)] for y, row in enumerate(terrain)]
    words = source_text.split()
    if not words:
        return tuple(" " * WORLD_WIDTH for _ in range(WORLD_HEIGHT))
    words = rng.sample(words, min(len(words), 96))
    # Bound sampled words and combining sequences before repeating glyphs.
    # The loader has already made terminal controls safe, so these remain literal.
    glyphs = [(glyph[:8], cells) for word in words
              for _, glyph, cells in visible_cells(word[:64], 0, line_width(word[:64]))
              if not glyph[0].isspace()]
    if not glyphs:
        return tuple(" " * WORLD_WIDTH for _ in range(WORLD_HEIGHT))
    narrow = [glyph for glyph, cells in glyphs if cells == 1]
    rows = []
    for y, row in enumerate(terrain):
        parts = []
        x = 0
        while x < WORLD_WIDTH:
            glyph, cells = " ", 1
            if paint[y][x]:
                glyph, cells = rng.choice(glyphs)
                # A wide glyph must fit entirely inside one scenery role; it
                # cannot cover a trunk, shoreline, or unpainted neighbor by chance.
                if cells == 2 and (x + 1 == WORLD_WIDTH or row[x + 1] != row[x]
                                   or not paint[y][x + 1]):
                    glyph, cells = (rng.choice(narrow) if narrow else " "), 1
            parts.append(glyph)
            x += cells
        rows.append("".join(parts))
    return tuple(rows)


def generate_world(source_text: str, seed: str) -> World:
    """Generate repeatable terrain first; source glyphs only decorate the result."""
    rng = random.Random(int.from_bytes(
        sha256(seed.encode("utf-8", errors="surrogatepass")).digest(), "big"))
    terrain = [[Terrain.MOSS] * WORLD_WIDTH for _ in range(WORLD_HEIGHT)]
    spawn = (6, WORLD_HEIGHT // 2)
    # Broad overlapping patches suggest ground cover rather than prescribed paths.
    # Keep patch density consistent when the trial world dimensions change.
    for _ in range(WORLD_WIDTH * WORLD_HEIGHT // 60):
        kind = rng.choice((Terrain.GRASS, Terrain.GRASS, Terrain.EARTH))
        for x, y in _ellipse(rng.randrange(WORLD_WIDTH), rng.randrange(WORLD_HEIGHT),
                             rng.randrange(4, 10), rng.randrange(2, 5)):
            terrain[y][x] = kind
    pond = (rng.randrange(WORLD_WIDTH * 65 // 100, WORLD_WIDTH * 81 // 100),
            rng.randrange(WORLD_HEIGHT * 30 // 100, WORLD_HEIGHT * 70 // 100))
    for x, y in _ellipse(*pond, 8, 4):
        terrain[y][x] = Terrain.EARTH
    for x, y in _ellipse(*pond, 6, 3):
        terrain[y][x] = Terrain.WATER

    # Small separated cores give trees collision without forming walls. Leaves
    # remain passable, and the pond retains a generous surrounding bank.
    for _ in range(WORLD_WIDTH * WORLD_HEIGHT // 60):
        cx, cy = rng.randrange(3, WORLD_WIDTH - 4), rng.randrange(2, WORLD_HEIGHT - 2)
        if abs(cx - spawn[0]) < 8 and abs(cy - spawn[1]) < 4:
            continue
        # Keep canopies apart as well as cores: open woodland, not a carpet.
        if any(terrain[y][x] in BLOCKED or terrain[y][x] == Terrain.CANOPY
               for x, y in _ellipse(cx, cy, 6, 3)):
            continue
        for x, y in _ellipse(cx, cy, 4, 2):
            if terrain[y][x] != Terrain.WATER:
                terrain[y][x] = Terrain.CANOPY
        terrain[cy][cx] = terrain[cy][cx + 1] = Terrain.TRUNK
    for x, y in _ellipse(*spawn, 5, 2):
        terrain[y][x] = Terrain.EARTH

    # Occasional small blooms decorate walkable ground without adding collisions.
    for _ in range(WORLD_WIDTH * WORLD_HEIGHT // 240):
        cx, cy = rng.randrange(2, WORLD_WIDTH - 2), rng.randrange(2, WORLD_HEIGHT - 2)
        bloom = ((cx - 1, cy), (cx, cy), (cx + 1, cy))
        if all(terrain[y][x] in (Terrain.MOSS, Terrain.GRASS) for x, y in bloom):
            for x, y in bloom:
                terrain[y][x] = Terrain.FLOWER

    # Connectivity is a requirement, not a maze-building strategy. In the rare
    # case that cores enclose ground, make their leaves traversable instead.
    count = sum(cell not in BLOCKED for row in terrain for cell in row)
    if len(_reachable(terrain, spawn)) != count:
        terrain = [[Terrain.CANOPY if cell == Terrain.TRUNK else cell
                    for cell in row] for row in terrain]
    return World(tuple(tuple(row) for row in terrain), _text_rows(source_text, terrain, rng),
                 spawn, pond)
