"""Coordinated fixed and seeded palettes, separate from light intensity calculations."""

from colorsys import hls_to_rgb
from dataclasses import dataclass
from hashlib import sha256


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

    background: tuple[int, int, int] = (12, 16, 26)  # Moonlight darkness.
    foreground: tuple[int, int, int] = (184, 211, 235)  # Pale blue text.
    cell_background: tuple[int, int, int] = (37, 49, 66)
    cursor_background: tuple[int, int, int] = (170, 192, 240)  # Lavender cursor.

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
DEFAULT_THEME = "moonlight"
DEFAULT_SEED = "moss"
THEMES = ("moonlight", "forest")


def _rgb(hue: float, lightness: float, saturation: float) -> tuple[int, int, int]:
    """Convert a coordinated hue/lightness/saturation color into RGB channels."""
    red, green, blue = hls_to_rgb(hue / 360, lightness, saturation)
    return round(red * 255), round(green * 255), round(blue * 255)


def forest_palette(seed: str = DEFAULT_SEED) -> Palette:
    """Generate one repeatable forest palette, independent of source or position."""
    # Python's built-in hash changes between processes. SHA-256 gives the same
    # bytes on every launch; surrogatepass also accepts unusual shell arguments.
    values = sha256(seed.encode("utf-8", errors="surrogatepass")).digest()
    hue = 90 + 40 * values[0] / 255
    saturation = 0.25 + 0.15 * values[1] / 255
    # All green roles share a hue. Narrow lightness ranges keep lit text pale
    # against moss cells; the contrasting gold cursor stays easy to locate.
    return Palette(
        background=_rgb(hue, 0.05 + 0.025 * values[2] / 255, saturation),
        foreground=_rgb(hue, 0.78 + 0.06 * values[3] / 255, saturation),
        cell_background=_rgb(hue, 0.16 + 0.04 * values[4] / 255, saturation),
        cursor_background=_rgb(38 + 16 * values[5] / 255, 0.68, 0.65),
    )


def palette_for(theme: str, seed: str = DEFAULT_SEED) -> Palette:
    """Resolve a theme once at startup; renderers only receive its color roles."""
    if theme == "moonlight":
        return DEFAULT_PALETTE
    if theme == "forest":
        return forest_palette(seed)
    raise ValueError(f"Unknown theme: {theme}")
