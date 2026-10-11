"""Generate a seeded landscape with connected terrain and named landmarks."""

from collections import deque
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import random

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


def _scenery_rows(terrain: tuple[tuple[Terrain, ...], ...], seed: str) -> tuple[str, ...]:
    """Give terrain readable textures without changing placement or collisions."""
    # Separate random state keeps art edits from moving terrain or landmarks.
    rng = random.Random(sha256(seed.encode("utf-8", errors="surrogatepass")
                               + b"\0scenery").digest())
    height, width = len(terrain), len(terrain[0])

    def neighbor(x: int, y: int) -> Terrain | None:
        return terrain[y][x] if 0 <= x < width and 0 <= y < height else None

    rows = []
    for y, row in enumerate(terrain):
        parts = []
        for x, kind in enumerate(row):
            glyph = " "
            if kind == Terrain.CANOPY:
                leaves = (Terrain.CANOPY, Terrain.TRUNK)
                around = sum(neighbor(nx, ny) in leaves for nx, ny in
                             ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)))
                # Soft rims and denser interiors read as leafy crowns, rather
                # than unrelated characters spread across a colored patch.
                glyph = "·" if around < 3 else rng.choice("░░▒")
            elif kind == Terrain.TRUNK:
                glyph = "║"
            elif kind == Terrain.WATER:
                # Calm broken ripple bands leave enough solid blue to read water.
                if y % 2 == 0 and (x + y) % 5 < 3:
                    glyph = "~"
            elif kind in (Terrain.FLOWER, Terrain.GOLD_FLOWER):
                glyph = "*" if neighbor(x - 1, y) == kind and neighbor(x + 1, y) == kind else "·"
            elif kind == Terrain.TALL_GRASS:
                glyph = rng.choice("╱│╲ ")
            elif kind == Terrain.ROCK:
                glyph = "▒" if neighbor(x, y - 1) == Terrain.ROCK else "▄"
            elif kind == Terrain.CRYSTAL:
                glyph = "◆"
            elif kind == Terrain.BRIDGE:
                glyph = "═" if neighbor(x, y - 1) != kind or neighbor(x, y + 1) != kind else "│"
            elif kind == Terrain.STEPPING_STONE:
                glyph = "▪"
            elif kind == Terrain.RUIN:
                # Connected masonry distinguishes a lintel from upright pillars.
                left, right = neighbor(x - 1, y) == kind, neighbor(x + 1, y) == kind
                below = neighbor(x, y + 1) == kind
                if below and right and not left:
                    glyph = "┌"
                elif below and left and not right:
                    glyph = "┐"
                else:
                    glyph = "─" if left or right else "│"
            elif kind == Terrain.LANTERN:
                glyph = "✦" if neighbor(x - 1, y) == kind and neighbor(x + 1, y) == kind else "·"
            parts.append(glyph)
        rows.append("".join(parts))
    return tuple(rows)


def _paint(terrain: list[list[Terrain]], kind: Terrain,
           center: tuple[int, int], rx: int, ry: int) -> None:
    for x, y in _ellipse(*center, rx, ry):
        terrain[y][x] = kind


def generate_world(seed: str) -> World:
    """Place distinct landscape pockets, then give them curated scenery textures."""
    rng = random.Random(int.from_bytes(
        sha256(seed.encode("utf-8", errors="surrogatepass")).digest(), "big"))
    terrain = [[Terrain.MOSS] * WORLD_WIDTH for _ in range(WORLD_HEIGHT)]
    spawn = (6, WORLD_HEIGHT // 2)
    for _ in range(WORLD_WIDTH * WORLD_HEIGHT // 60):
        _paint(terrain, rng.choice((Terrain.GRASS, Terrain.GRASS, Terrain.EARTH)),
               (rng.randrange(WORLD_WIDTH), rng.randrange(WORLD_HEIGHT)),
               rng.randrange(4, 10), rng.randrange(2, 5))

    # Separate regions keep landmarks distinct while their details vary with the seed.
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
    cells = tuple(tuple(row) for row in terrain)
    return World(cells, _scenery_rows(cells, seed), spawn, pond, landmarks)
