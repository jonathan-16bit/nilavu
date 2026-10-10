"""Choose the visible document rectangle without depending on the terminal UI."""

from dataclasses import dataclass

from nilavu.navigation import LightPosition


@dataclass(frozen=True)
class Viewport:
    """Document coordinates of the screen's top-left corner."""

    x: int = 0
    y: int = 0

    def follow(
        self,
        light: LightPosition,
        width: int,
        height: int,
        *,
        margin_x: int = 0,
        margin_y: int = 0,
    ) -> "Viewport":
        """Keep the light inside inset screen edges, staying within the document."""
        # A widget can temporarily have no area during layout. Wait for a real
        # size instead of moving the view in response to an invisible screen.
        if width <= 0 or height <= 0:
            return self

        def origin(current: int, position: int, last: int, size: int, margin: int) -> int:
            # Leave at least one cell between the inset edges on small screens.
            # This prevents conflicting margins from pushing the view back and forth.
            margin = max(0, min(margin, (size - 1) // 2))
            # Move only when the light crosses an inset edge. Document boundaries
            # take precedence: avoid scrolling into empty space to satisfy a margin.
            start = min(current, position - margin)
            start = max(start, position - size + 1 + margin)
            return max(0, min(start, last + 1 - size))

        return Viewport(
            origin(self.x, light.x, light.max_x, width, margin_x),
            origin(self.y, light.y, light.max_y, height, margin_y),
        )
