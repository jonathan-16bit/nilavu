"""Decorative companions follow a bounded trail without affecting collection."""

from dataclasses import dataclass, replace
import math

from nilavu.lighting import brightness_at
from nilavu.fireflies import FIREFLY_COUNT
from nilavu.palette import SHADE_LEVELS
from nilavu.world import World

TRAIL_SPACING = 2
COMPANION_RADIUS = 6.0


def _quiet_positions(world: World, cursor: tuple[int, int], targets: tuple[tuple[int, int], ...],
                     cell_aspect_ratio: float) -> tuple[tuple[int, int], ...]:
    """Prefer blank ground near each target, keeping symbols and companions clear."""
    cx, cy = cursor
    ry = math.ceil(min(world.height, 12 / cell_aspect_ratio))
    candidates = [(x, y) for y in range(max(0, cy - ry), min(world.height, cy + ry + 1))
                  for x in range(max(0, cx - 12), min(world.width, cx + 13))
                  if world.passable(x, y) and world.lines[y][x] == " "
                  and (x, y) != cursor
                  and math.hypot(x - cx, (y - cy) * cell_aspect_ratio) <= 12]
    positions = []
    for tx, ty in targets:
        available = [cell for cell in candidates if cell not in positions]
        position = min(available,
                       key=lambda p: math.hypot(p[0] - tx, (p[1] - ty) * cell_aspect_ratio),
                       default=cursor)
        # If there is no clear cell, the glow can share the cursor temporarily.
        # The renderer always gives the cursor priority over a companion body.
        positions.append(position)
    return tuple(positions)


@dataclass(frozen=True)
class Companions:
    """Wake order controls trail spacing; the history stays small even on long walks."""

    trail: tuple[tuple[int, int], ...]
    positions: tuple[tuple[int, int], ...] = ()
    idle_ticks: int = 0

    def add(self, position: tuple[int, int]) -> "Companions":
        return replace(self, positions=self.positions + (position,))

    def follow(self, world: World, cursor: tuple[int, int], cell_aspect_ratio: float) -> "Companions":
        trail = (cursor,) + self.trail[:TRAIL_SPACING * FIREFLY_COUNT]
        targets = tuple(trail[min((i + 1) * TRAIL_SPACING, len(trail) - 1)]
                        for i in range(len(self.positions)))
        positions = _quiet_positions(world, cursor, targets, cell_aspect_ratio) if targets else ()
        # Deriving positions from the recent trail makes catch-up automatic,
        # regardless of how many movement events arrive between timer ticks.
        return Companions(trail, positions)

    def idle(self, world: World, cell_aspect_ratio: float) -> "Companions":
        if not self.positions:
            return self
        ticks = min(2, self.idle_ticks + 1)
        if ticks < 2:
            return replace(self, idle_ticks=ticks)
        x, y = self.trail[0]
        offsets = ((-2, -1), (2, -1), (0, 1))
        targets = tuple((x + dx, y + dy) for dx, dy in offsets[:len(self.positions)])
        return replace(self, idle_ticks=ticks,
                       positions=_quiet_positions(world, (x, y), targets, cell_aspect_ratio))


def companion_glow(world: World, positions: tuple[tuple[int, int], ...],
                   cell_aspect_ratio: float) -> dict[tuple[int, int], float]:
    """Build small steady halos only when companion positions change."""
    ry = math.ceil(min(world.height, COMPANION_RADIUS / cell_aspect_ratio))
    rx = math.ceil(min(world.width, COMPANION_RADIUS))
    light = {}
    for cx, cy in positions:
        for y in range(max(0, cy - ry), min(world.height, cy + ry + 1)):
            for x in range(max(0, cx - rx), min(world.width, cx + rx + 1)):
                value = 0.65 * brightness_at(x, y, cx, cy, COMPANION_RADIUS,
                                             cell_aspect_ratio=cell_aspect_ratio)
                level = int(value * (SHADE_LEVELS - 1) + 0.5)
                if level:
                    light[x, y] = max(light.get((x, y), 0), level / (SHADE_LEVELS - 1))
    return light
