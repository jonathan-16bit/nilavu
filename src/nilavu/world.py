"""Generate a small open woodland independently of source-file structure."""

from collections import deque
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import random

from nilavu.cells import line_width, visible_cells
from nilavu.navigation import LightPosition

WORLD_WIDTH = 100
WORLD_HEIGHT = 40


class Terrain(Enum):
    MOSS = "moss"
    GRASS = "grass"
    EARTH = "earth"
    CANOPY = "canopy"
    TRUNK = "trunk"
    WATER = "water"


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


def _text_rows(source_text: str, rng: random.Random) -> tuple[str, ...]:
    """Sample across the input, reusing short material without filling every cell."""
    words = source_text.split()
    if not words:
        return tuple(" " * WORLD_WIDTH for _ in range(WORLD_HEIGHT))
    words = rng.sample(words, min(len(words), 96))
    # Limit both characters and terminal columns. A pathological combining-mark
    # sequence must not become an enormous glyph repeated throughout the world.
    words = ["".join(glyph for _, glyph, _ in visible_cells(
        word[:64], 0, min(14, line_width(word[:64])))) for word in words]
    rows = []
    for _ in range(WORLD_HEIGHT):
        parts = [" " * rng.randrange(2, 7)]
        column = len(parts[0])
        while column < WORLD_WIDTH:
            word = rng.choice(words)
            width = line_width(word)
            gap = rng.randrange(3, 8)
            if column + width + gap > WORLD_WIDTH:
                break
            parts.extend((word, " " * gap))
            column += width + gap
        parts.append(" " * (WORLD_WIDTH - column))
        rows.append("".join(parts))
    return tuple(rows)


def generate_world(source_text: str, seed: str) -> World:
    """Generate repeatable terrain first; source words only decorate the result."""
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
    for _ in range(WORLD_WIDTH * WORLD_HEIGHT // 18):
        cx, cy = rng.randrange(3, WORLD_WIDTH - 4), rng.randrange(2, WORLD_HEIGHT - 2)
        if abs(cx - spawn[0]) < 8 and abs(cy - spawn[1]) < 4:
            continue
        if any(terrain[y][x] in BLOCKED
               for x, y in _ellipse(cx, cy, 4, 2)):
            continue
        for x, y in _ellipse(cx, cy, 4, 2):
            if terrain[y][x] != Terrain.WATER:
                terrain[y][x] = Terrain.CANOPY
        terrain[cy][cx] = terrain[cy][cx + 1] = Terrain.TRUNK
    for x, y in _ellipse(*spawn, 5, 2):
        terrain[y][x] = Terrain.EARTH

    # Connectivity is a requirement, not a maze-building strategy. In the rare
    # case that cores enclose ground, make their leaves traversable instead.
    count = sum(cell not in BLOCKED for row in terrain for cell in row)
    if len(_reachable(terrain, spawn)) != count:
        terrain = [[Terrain.CANOPY if cell == Terrain.TRUNK else cell
                    for cell in row] for row in terrain]
    return World(tuple(tuple(row) for row in terrain), _text_rows(source_text, rng),
                 spawn, pond)
