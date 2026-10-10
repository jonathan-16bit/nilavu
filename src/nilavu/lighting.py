"""Pure brightness calculations, independent of terminal colors and rendering."""

import math


def brightness_at(
    x: int, y: int, light_x: int, light_y: int, radius: float
) -> float:
    """Return smoothstep brightness from 0 (dark) to 1 (fully illuminated).

    Coordinates use the same character/line units as light-position state.
    Both axes have equal weight for now. The radius must be finite and positive;
    the light center is fully bright and positions at or beyond the radius
    are dark.
    """
    # Zero/negative radii cannot describe a light region. NaN and infinity would
    # otherwise silently produce misleading brightness or destroy the boundary.
    if not math.isfinite(radius) or radius <= 0:
        raise ValueError("Light radius must be finite and positive.")

    # Relative offsets make the result depend on distance from the light, not
    # where the light happens to sit in the document. hypot measures Euclidean
    # distance: sqrt(dx * dx + dy * dy).
    distance = math.hypot(x - light_x, y - light_y)
    if distance >= radius:
        return 0.0

    # Remaining distance is 1 at the center and 0 at the radius. Smoothstep
    # bends that linear ramp so its slope is zero at both ends: brightness
    # leaves the center gently and reaches darkness without an abrupt edge.
    remaining = 1.0 - distance / radius
    return remaining * remaining * (3.0 - 2.0 * remaining)
