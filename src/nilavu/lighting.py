"""Pure brightness calculations, independent of terminal colors and rendering."""

import math


def brightness_at(
    x: int,
    y: int,
    light_x: int,
    light_y: int,
    radius: float,
    *,
    cell_aspect_ratio: float = 1.0,
) -> float:
    """Return smoothstep brightness from 0 (dark) to 1 (fully illuminated).

    Coordinates use the same character/line units as light-position state.
    cell_aspect_ratio is cell height divided by cell width: 2.0 counts a row
    as two column units. The default 1.0 retains equal-axis distance for callers
    without cell geometry. Radius and ratio must be finite and positive.
    The center is fully bright; positions at or beyond the radius are dark.
    """
    # Zero/negative radii cannot describe a light region. NaN and infinity would
    # otherwise silently produce misleading brightness or destroy the boundary.
    if not math.isfinite(radius) or radius <= 0:
        raise ValueError("Light radius must be finite and positive.")
    if not math.isfinite(cell_aspect_ratio) or cell_aspect_ratio <= 0:
        raise ValueError("Cell aspect ratio must be finite and positive.")

    # Relative offsets make the result depend on distance from the light, not
    # where the light happens to sit in the document. hypot measures Euclidean
    # distance. Scaling the row offset accounts for taller terminal cells without
    # changing movement coordinates or introducing terminal-specific queries.
    distance = math.hypot(x - light_x, (y - light_y) * cell_aspect_ratio)
    if distance >= radius:
        return 0.0

    # Remaining distance is 1 at the center and 0 at the radius. Smoothstep
    # bends that linear ramp so its slope is zero at both ends: brightness
    # leaves the center gently and reaches darkness without an abrupt edge.
    remaining = 1.0 - distance / radius
    return remaining * remaining * (3.0 - 2.0 * remaining)
