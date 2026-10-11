"""Generate a open landscape independently of source-file structure."""

from collections import deque
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import random

from nilavu.cells import line_width, visible_cells
from nilavu.navigation import LightPosition

WORLD_WIDTH = 180
WORLD_HEIGHT = 48


class Terrain(Enum):
    MOSS = "moss"
    GRASS = "grass"
    EARTH = "earth"
    CANOPY = "canopy"
    TRUNK = "trunk"
    WATER = "water"
    FLOWER = "flower"
    GOLD_FLOWER = "gold_flower"
    MEADOW = "meadow"
    TALL_GRASS = "tall_grass"
    STONE = "stone"
    ROCK = "rock"
    CRYSTAL = "crystal"
    BRIDGE = "bridge"
    STEPPING_STONE = "stepping_stone"
    RUIN = "ruin"
    LANTERN = "lantern"


BLOCKED = frozenset((Terrain.TRUNK, Terrain.WATER, Terrain.ROCK, Terrain.CRYSTAL, Terrain.RUIN))


@dataclass(frozen=True)
class Landmark:
    """A named, reachable place that can anchor later firefly placement."""

    name: str
    position: tuple[int, int]


@dataclass(frozen=True)
class World:
    """An immutable cell map, fixed for the lifetime of an exploration run."""

    terrain: tuple[tuple[Terrain, ...], ...]
    lines: tuple[str, ...]
    spawn: tuple[int, int]
    pond: tuple[int, int]
    landmarks: tuple[Landmark, ...]

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


def _connect_ground(terrain: list[list[Terrain]], spawn: tuple[int, int]) -> None:
    """Open a short route from trapped ground without removing entire groves."""
    reached = _reachable(terrain, spawn)
    pockets = [(x, y) for y, row in enumerate(terrain) for x, kind in enumerate(row)
               if kind not in BLOCKED and (x, y) not in reached]
    for pocket in pockets:
        if pocket in reached:
            continue
        # Water and ruins are fixed landmarks. Only decorative obstacles may be
        # opened, and parent links identify one connecting route through them.
        parents = {pocket: None}
        queue = deque([pocket])
        while queue:
            cell = queue.popleft()
            if cell in reached:
                break
            x, y = cell
            for next_cell in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                nx, ny = next_cell
                if (0 <= nx < WORLD_WIDTH and 0 <= ny < WORLD_HEIGHT
                        and next_cell not in parents
                        and terrain[ny][nx] not in (Terrain.WATER, Terrain.RUIN)):
                    parents[next_cell] = cell
                    queue.append(next_cell)
        else:
            raise ValueError("landscape has no route to a ground pocket")
        while cell is not None:
            x, y = cell
            if terrain[y][x] == Terrain.TRUNK:
                terrain[y][x] = Terrain.CANOPY
            elif terrain[y][x] in (Terrain.ROCK, Terrain.CRYSTAL):
                terrain[y][x] = Terrain.STONE
            cell = parents[cell]
        reached = _reachable(terrain, spawn)


def _text_rows(source_text: str, terrain: list[list[Terrain]],
               rng: random.Random) -> tuple[str, ...]:
    """Arrange source glyphs along terrain shapes, rather than scattering words."""
    # Leave ordinary ground blank so scenery and collision cores stand out.
    # Dense leaves reveal canopy outlines; water has broken ripple rows.
    density = {Terrain.MOSS: 0.0, Terrain.GRASS: 0.0, Terrain.EARTH: 0.0,
               Terrain.CANOPY: 0.72, Terrain.TRUNK: 1.0, Terrain.FLOWER: 1.0,
               Terrain.GOLD_FLOWER: 1.0, Terrain.MEADOW: 0.0,
               Terrain.TALL_GRASS: 0.75, Terrain.STONE: 0.0,
               Terrain.ROCK: 0.80, Terrain.CRYSTAL: 1.0, Terrain.BRIDGE: 1.0,
               Terrain.STEPPING_STONE: 1.0, Terrain.RUIN: 1.0, Terrain.LANTERN: 1.0}
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


def _paint(terrain: list[list[Terrain]], kind: Terrain,
           center: tuple[int, int], rx: int, ry: int) -> None:
    for x, y in _ellipse(*center, rx, ry):
        terrain[y][x] = kind


def generate_world(source_text: str, seed: str) -> World:
    """Place distinct landscape pockets, then decorate them with source glyphs."""
    rng = random.Random(int.from_bytes(
        sha256(seed.encode("utf-8", errors="surrogatepass")).digest(), "big"))
    terrain = [[Terrain.MOSS] * WORLD_WIDTH for _ in range(WORLD_HEIGHT)]
    spawn = (6, WORLD_HEIGHT // 2)
    for _ in range(WORLD_WIDTH * WORLD_HEIGHT // 60):
        _paint(terrain, rng.choice((Terrain.GRASS, Terrain.GRASS, Terrain.EARTH)),
               (rng.randrange(WORLD_WIDTH), rng.randrange(WORLD_HEIGHT)),
               rng.randrange(4, 10), rng.randrange(2, 5))

    # Separate regions keep landmarks distinct without relying on source meaning.
    meadow = (rng.randrange(30, 46), rng.randrange(9, 15))
    garden = (rng.randrange(112, 128), rng.randrange(32, 38))
    arch = (rng.randrange(132, 146), rng.randrange(10, 16))
    lantern = (rng.randrange(35, 51), rng.randrange(33, 39))
    pond = (rng.randrange(150, 165), rng.randrange(29, 37))
    landmarks = (Landmark("meadow", meadow), Landmark("rock garden", garden),
                 Landmark("ruined arch", arch), Landmark("lantern clearing", lantern))
    for center, kind, rx, ry in ((meadow, Terrain.MEADOW, 19, 7),
                                (garden, Terrain.STONE, 15, 6),
                                (arch, Terrain.EARTH, 11, 5),
                                (lantern, Terrain.EARTH, 10, 5),
                                (pond, Terrain.EARTH, 11, 5)):
        _paint(terrain, kind, center, rx, ry)
    _paint(terrain, Terrain.WATER, pond, 8, 4)

    # A narrow wandering stream crosses the map. Two guaranteed crossings make
    # both banks accessible, even before optional scenery is placed.
    stream = []
    cx = rng.randrange(83, 94)
    for y in range(WORLD_HEIGHT):
        cx = max(81, min(96, cx + rng.choice((-1, 0, 0, 1))))
        stream.append(cx)
        for x in range(cx - 1, cx + 3):
            terrain[y][x] = Terrain.EARTH
        terrain[y][cx] = terrain[y][cx + 1] = Terrain.WATER
    bridge_y = WORLD_HEIGHT // 2
    for y in range(bridge_y - 1, bridge_y + 2):
        for x in range(min(stream[bridge_y - 1:bridge_y + 2]) - 3,
                       max(stream[bridge_y - 1:bridge_y + 2]) + 5):
            terrain[y][x] = Terrain.BRIDGE
    stones_y = 10
    for x in range(stream[stones_y], stream[stones_y] + 2):
        terrain[stones_y][x] = Terrain.STEPPING_STONE
    landmarks += (Landmark("bridge", (stream[bridge_y], bridge_y)),
                  Landmark("stepping stones", (stream[stones_y], stones_y)),
                  Landmark("pond bank", (pond[0] - 9, pond[1])))

    # Groves are denser locally, with open surroundings around each landmark.
    groves = ((22, 25), (62, 20), (64, 39), (113, 14), (165, 12))
    for _ in range(WORLD_WIDTH * WORLD_HEIGHT // 32):
        gx, gy = rng.choice(groves)
        cx, cy = gx + rng.randrange(-15, 16), gy + rng.randrange(-7, 8)
        if not (4 <= cx < WORLD_WIDTH - 5 and 3 <= cy < WORLD_HEIGHT - 3):
            continue
        if abs(cx - spawn[0]) < 8 and abs(cy - spawn[1]) < 4:
            continue
        if any(abs(cx - mark.position[0]) < 17 and abs(cy - mark.position[1]) < 8
               for mark in landmarks):
            continue
        if any(terrain[y][x] not in (Terrain.MOSS, Terrain.GRASS, Terrain.EARTH)
               for x, y in _ellipse(cx, cy, 5, 2)):
            continue
        _paint(terrain, Terrain.CANOPY, (cx, cy), 4, 2)
        terrain[cy][cx] = terrain[cy][cx + 1] = Terrain.TRUNK

    # Meadows carry intentional grass tufts and colorful blooms; ordinary ground
    # remains blank. Placement cannot alter the stream or its crossings.
    for _ in range(65):
        cx, cy = meadow[0] + rng.randrange(-17, 18), meadow[1] + rng.randrange(-6, 7)
        cells = tuple(_ellipse(cx, cy, 2, 1))
        if cells and all(terrain[y][x] == Terrain.MEADOW for x, y in cells):
            for x, y in cells:
                terrain[y][x] = Terrain.TALL_GRASS
            bloom = rng.choice((Terrain.FLOWER, Terrain.GOLD_FLOWER))
            for x in range(cx - 1, cx + 2):
                terrain[cy][x] = bloom
    for _ in range(25):
        cx, cy = garden[0] + rng.randrange(-12, 13), garden[1] + rng.randrange(-4, 5)
        cells = tuple(_ellipse(cx, cy, 2, 1))
        if (cells and all(terrain[y][x] == Terrain.STONE for x, y in cells)
                and not any(abs(x - garden[0]) < 3 and abs(y - garden[1]) < 2
                            for x, y in cells)):
            for x, y in cells:
                terrain[y][x] = Terrain.ROCK
            # Sparkling tips are decoration; the surrounding rock still blocks.
            terrain[cy][cx] = Terrain.CRYSTAL
    # Broken stone sides and a lintel frame a walkable center passage.
    ax, ay = arch
    for x in range(ax - 5, ax + 6):
        if x != ax + 2:
            terrain[ay - 2][x] = Terrain.RUIN
    for y in range(ay - 1, ay + 2):
        terrain[y][ax - 5] = terrain[y][ax + 5] = Terrain.RUIN
    lx, ly = lantern
    _paint(terrain, Terrain.LANTERN, lantern, 1, 1)
    for x, y in _ellipse(lx, ly, 7, 3):
        if terrain[y][x] == Terrain.EARTH and (x + y) % 5 == 0:
            terrain[y][x] = Terrain.GOLD_FLOWER
    _paint(terrain, Terrain.EARTH, spawn, 5, 2)

    _connect_ground(terrain, spawn)
    return World(tuple(tuple(row) for row in terrain), _text_rows(source_text, terrain, rng),
                 spawn, pond, landmarks)
