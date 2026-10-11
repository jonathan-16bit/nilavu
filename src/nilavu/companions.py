"""Decorative companions follow a bounded trail without affecting collection."""

from dataclasses import dataclass, replace
import math

from nilavu.lighting import brightness_at
from nilavu.fireflies import FIREFLY_COUNT
from nilavu.palette import SHADE_LEVELS
from nilavu.world import World

TRAIL_SPACING = 2
# A close glow identifies the body without creating another broad light circle.
COMPANION_RADIUS = 3.0


def _quiet_positions(world: World, cursor: tuple[int, int], targets: tuple[tuple[int, int], ...],
                     cell_aspect_ratio: float,
                     occupied: tuple[tuple[int, int], ...] = ()) -> tuple[tuple[int, int], ...]:
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
        available = [cell for cell in candidates if cell not in positions and cell not in occupied]
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
    def add(self, world: World, position: tuple[int, int], cell_aspect_ratio: float) -> "Companions":
        # Place the new body immediately, without moving existing companions or
        # requiring a later timer-driven rearrangement to make it visible.
        placed = _quiet_positions(world, self.trail[0], (position,),
                                  cell_aspect_ratio, occupied=self.positions)
        return replace(self, positions=self.positions + placed)

    def follow(self, world: World, cursor: tuple[int, int], cell_aspect_ratio: float) -> "Companions":
        trail = (cursor,) + self.trail[:TRAIL_SPACING * FIREFLY_COUNT]
        targets = tuple(trail[min((i + 1) * TRAIL_SPACING, len(trail) - 1)]
                        for i in range(len(self.positions)))
        positions = _quiet_positions(world, cursor, targets, cell_aspect_ratio) if targets else ()
        # Deriving positions from the recent trail makes catch-up automatic,
        # regardless of how many movement events arrive between timer ticks.
        return Companions(trail, positions)

    def gather_at_pond(self, world: World, cursor: tuple[int, int],
                       cell_aspect_ratio: float) -> "Companions":
        """Settle on clear shore cells once; later exploration leaves them here."""
        x, y = world.pond_bank
        targets = ((x - 2, y - 1), (x - 2, y + 1), (x, y + 2))
        return replace(self, positions=_quiet_positions(
            world, cursor, targets[:len(self.positions)], cell_aspect_ratio))


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
