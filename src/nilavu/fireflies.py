"""Deterministic discoveries and one-way waking, independent of the terminal UI."""

from dataclasses import dataclass, replace
from hashlib import sha256
import math
import random

from nilavu.lighting import brightness_at
from nilavu.object_lighting import ANIMATION_FRAMES
from nilavu.palette import SHADE_LEVELS
from nilavu.world import Terrain, World

FIREFLY_COUNT = 3
INTERACTION_RADIUS = 3.0
GLOW_RADIUS = 5.0


@dataclass(frozen=True)
class Firefly:
    position: tuple[int, int]
    awake: bool = False


@dataclass(frozen=True)
class FireflyRun:
    """Collected discoveries belong to one world and cannot be counted twice."""

    fireflies: tuple[Firefly, ...]
    completed: bool = False

    @property
    def awake_count(self) -> int:
        return sum(fly.awake for fly in self.fireflies)

    def nearest_sleeping(self, position: tuple[int, int], cell_aspect_ratio: float) -> int | None:
        if not math.isfinite(cell_aspect_ratio) or cell_aspect_ratio <= 0:
            raise ValueError("Cell aspect ratio must be finite and positive.")
        x, y = position
        candidates = [(math.hypot(fly.position[0] - x,
                                  (fly.position[1] - y) * cell_aspect_ratio), i)
                      for i, fly in enumerate(self.fireflies) if not fly.awake]
        distance, index = min(candidates, default=(math.inf, -1))
        return index if distance <= INTERACTION_RADIUS else None

    def wake_nearby(self, position: tuple[int, int], cell_aspect_ratio: float) -> "FireflyRun":
        index = self.nearest_sleeping(position, cell_aspect_ratio)
        if index is None:
            return self
        flies = list(self.fireflies)
        flies[index] = replace(flies[index], awake=True)
        return replace(self, fireflies=tuple(flies))

    def finish_nearby(self, world: World, position: tuple[int, int],
                      cell_aspect_ratio: float) -> "FireflyRun":
        # Completion depends on permanent collection, never decorative follower
        # positions. An explicit interaction at the shore is still required.
        if (not self.completed and self.fireflies
                and self.awake_count == len(self.fireflies)
                and at_pond_bank(world, position, cell_aspect_ratio)):
            return replace(self, completed=True)
        return self


def at_pond_bank(world: World, position: tuple[int, int], cell_aspect_ratio: float) -> bool:
    """Allow a close shore interaction, using the same geometry as waking."""
    if not math.isfinite(cell_aspect_ratio) or cell_aspect_ratio <= 0:
        raise ValueError("Cell aspect ratio must be finite and positive.")
    x, y = position
    px, py = world.pond_bank
    return (world.passable(x, y)
            and math.hypot(x - px, (y - py) * cell_aspect_ratio) <= INTERACTION_RADIUS)


def new_run(world: World, seed: str, count: int = FIREFLY_COUNT) -> FireflyRun:
    """Place quiet, reachable discoveries near distinct landmarks, with separate RNG."""
    names = ("meadow", "ruined arch", "rock garden")
    if not 1 <= count <= len(names):
        raise ValueError("Firefly count must be between one and three.")
    rng = random.Random(sha256(seed.encode("utf-8", errors="surrogatepass")
                               + b"\0fireflies").digest())
    marks = {mark.name: mark.position for mark in world.landmarks}
    flies = []
    quiet = (Terrain.MOSS, Terrain.GRASS, Terrain.EARTH, Terrain.MEADOW, Terrain.STONE)
    for name in names[:count]:
        cx, cy = marks[name]
        candidates = [(x, y) for y in range(max(0, cy - 3), min(world.height, cy + 4))
                      for x in range(max(0, cx - 7), min(world.width, cx + 8))
                      if world.terrain[y][x] in quiet and world.lines[y][x] == " "
                      and (x, y) != world.spawn
                      # Keep discoveries apart, even at the closest landmark edges.
                      and all(abs(fly.position[0] - x) + abs(fly.position[1] - y) > 20
                              for fly in flies)]
        if not candidates:
            raise ValueError("Landmark has no quiet ground for a firefly.")
        flies.append(Firefly(rng.choice(candidates)))
    return FireflyRun(tuple(flies))


def sleeping_glow_frames(world: World, position: tuple[int, int],
                         cell_aspect_ratio: float) -> tuple[dict[tuple[int, int], float], ...]:
    """Cache a small pulsing halo; visibility relative to the cursor stays in the UI."""
    if not math.isfinite(cell_aspect_ratio) or cell_aspect_ratio <= 0:
        raise ValueError("Cell aspect ratio must be finite and positive.")
    cx, cy = position
    rx = math.ceil(min(world.width, GLOW_RADIUS))
    ry = math.ceil(min(world.height, GLOW_RADIUS / cell_aspect_ratio))
    frames = []
    for frame in range(ANIMATION_FRAMES):
        strength = 0.42 + 0.10 * math.sin(math.tau * frame / ANIMATION_FRAMES + cx + cy)
        cells = {}
        for y in range(max(0, cy - ry), min(world.height, cy + ry + 1)):
            for x in range(max(0, cx - rx), min(world.width, cx + rx + 1)):
                intensity = strength * brightness_at(x, y, cx, cy, GLOW_RADIUS,
                                                      cell_aspect_ratio=cell_aspect_ratio)
                level = int(intensity * (SHADE_LEVELS - 1) + 0.5)
                if level:
                    cells[x, y] = level / (SHADE_LEVELS - 1)
        frames.append(cells)
    return tuple(frames)
