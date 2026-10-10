"""Coordinated palette presets, separate from light intensity calculations."""

from dataclasses import dataclass


SHADE_LEVELS = 5


def _blend(
    start: tuple[int, int, int], end: tuple[int, int, int], amount: float
) -> str:
    red, green, blue = (
        round(dark + (light - dark) * amount)
        for dark, light in zip(start, end)
    )
    return f"#{red:02x}{green:02x}{blue:02x}"


@dataclass(frozen=True)
class Palette:
    """Coordinated source, cell, and cursor colors as RGB channels."""

    background: tuple[int, int, int] = (16, 16, 20)  # #101014
    foreground: tuple[int, int, int] = (190, 212, 146)  # Muted warm green.
    cell_background: tuple[int, int, int] = (48, 58, 42)
    cursor_background: tuple[int, int, int] = (213, 174, 102)  # Amber.

    def color_at(self, brightness: float) -> str:
        """Blend toward the background for an intensity from 0 through 1."""
        # Each channel travels along the same fraction of its color range. This
        # preserves the palette's identity while making distant text disappear.
        return _blend(self.background, self.foreground, brightness)

    def style_at(self, brightness: float) -> str:
        """Choose one of five coordinated foreground/background shade pairs."""
        # Round intensity to evenly spaced levels. The distance/falloff math stays
        # unchanged; this palette boundary gives it the approved stepped look.
        level = int(brightness * (SHADE_LEVELS - 1) + 0.5)
        stepped = level / (SHADE_LEVELS - 1)
        background = _blend(self.background, self.cell_background, stepped)
        return f"{self.color_at(stepped)} on {background}"

    def cursor_style(self) -> str:
        """Highlight the current cell with dark text on the palette's accent."""
        background = _blend(self.cursor_background, self.cursor_background, 0.0)
        return f"{self.color_at(0.0)} on {background}"


DEFAULT_PALETTE = Palette()
DEFAULT_THEME = "green"

# Each preset supplies the same four roles. Rendering never needs to know which
# theme was chosen; every preset uses the same light curve and five shade levels.
PALETTES = {
    DEFAULT_THEME: DEFAULT_PALETTE,
    "moonlight": Palette(
        background=(12, 16, 26),
        foreground=(184, 211, 235),
        cell_background=(37, 49, 66),
        cursor_background=(170, 192, 240),
    ),
    "ember": Palette(
        background=(24, 14, 12),
        foreground=(238, 190, 139),
        cell_background=(67, 40, 30),
        cursor_background=(246, 209, 113),
    ),
}
