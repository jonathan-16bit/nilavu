"""The small default palette, kept separate from light intensity calculations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    """Background and fully illuminated source colors as RGB channels."""

    background: tuple[int, int, int] = (16, 16, 20)  # #101014
    foreground: tuple[int, int, int] = (190, 212, 146)  # Muted warm green.

    def color_at(self, brightness: float) -> str:
        """Blend toward the background for an intensity from 0 through 1."""
        # Each channel travels along the same fraction of its color range. This
        # preserves the palette's identity while making distant text disappear.
        red, green, blue = (
            round(dark + (light - dark) * brightness)
            for dark, light in zip(self.background, self.foreground)
        )
        return f"#{red:02x}{green:02x}{blue:02x}"


DEFAULT_PALETTE = Palette()
