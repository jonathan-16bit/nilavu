"""Build stepped glow frames independently of cursor lighting."""

from dataclasses import dataclass
import math

from nilavu.lighting import brightness_at
from nilavu.palette import SHADE_LEVELS
from nilavu.world import Terrain, World

ANIMATION_FRAMES = 12
ANIMATION_INTERVAL = 0.5


@dataclass(frozen=True)
class Glow:
    """A quantized local light level and its color, shared by overlapping cells."""

    level: int = 0
    color: tuple[int, int, int] = (0, 0, 0)

    @property
    def brightness(self) -> float:
        return self.level / (SHADE_LEVELS - 1)


def glow_field(world: World, cell_aspect_ratio: float,
               *, frame: int | None = None) -> tuple[tuple[Glow, ...], ...]:
    """Cache bounded lantern/crystal halos; overlapping lights use the strongest."""
    if not math.isfinite(cell_aspect_ratio) or cell_aspect_ratio <= 0:
        raise ValueError("Cell aspect ratio must be finite and positive.")
    field = [[Glow()] * world.width for _ in range(world.height)]
    sources = [(x, y, 6.0, 0.65, (173, 133, 255), False)
               for y, row in enumerate(world.terrain) for x, kind in enumerate(row)
               if kind == Terrain.CRYSTAL]
    sources += [(mark.position[0], mark.position[1], 12.0, 1.0, (255, 183, 75), True)
                for mark in world.landmarks if mark.name == "lantern clearing"]
    for cx, cy, radius, strength, color, flicker in sources:
        if frame is not None:
            phase = math.tau * (frame % ANIMATION_FRAMES) / ANIMATION_FRAMES
            if flicker:
                # Two short cycles give the lantern a restrained, uneven flicker.
                strength *= 0.92 + 0.05 * math.cos(phase * 3) + 0.03 * math.cos(phase * 5)
            else:
                # Position offsets prevent every crystal from pulsing in unison.
                strength += 0.12 * math.sin(phase + cx * 0.37 + cy * 0.61)
        # Clamp before rounding: even unusual valid aspect ratios cannot produce
        # enormous ranges. Work stays bounded by the actual world dimensions.
        ry = math.ceil(min(world.height, radius / cell_aspect_ratio))
        rx = math.ceil(min(world.width, radius))
        for y in range(max(0, cy - ry), min(world.height, cy + ry + 1)):
            for x in range(max(0, cx - rx), min(world.width, cx + rx + 1)):
                brightness = strength * brightness_at(x, y, cx, cy, radius,
                                                       cell_aspect_ratio=cell_aspect_ratio)
                level = int(brightness * (SHADE_LEVELS - 1) + 0.5)
                if level > field[y][x].level:
                    field[y][x] = Glow(level, color)
    return tuple(tuple(row) for row in field)


def water_highlight(x: int, y: int, frame: int) -> bool:
    """Move sparse short highlights across water without changing its glyphs."""
    return (x - frame + 3 * y) % ANIMATION_FRAMES < 2
