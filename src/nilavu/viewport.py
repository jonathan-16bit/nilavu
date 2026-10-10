"""Choose the visible document rectangle without depending on the terminal UI."""

from dataclasses import dataclass

from nilavu.navigation import LightPosition


@dataclass(frozen=True)
class Viewport:
    """Document coordinates of the screen's top-left corner."""

    x: int = 0
    y: int = 0

    def follow(self, light: LightPosition, width: int, height: int) -> "Viewport":
        """Scroll only enough to include the light, staying within the document."""
        # A widget can temporarily have no area during layout. Wait for a real
        # size instead of moving the view in response to an invisible screen.
        if width <= 0 or height <= 0:
            return self

        def origin(current: int, position: int, last: int, size: int) -> int:
            # Keep an already visible position stationary. Crossing either edge
            # moves that edge to the light; growing the screen removes overscroll.
            start = min(current, position)
            start = max(start, position - size + 1)
            return max(0, min(start, last + 1 - size))

        return Viewport(
            origin(self.x, light.x, light.max_x, width),
            origin(self.y, light.y, light.max_y, height),
        )
