"""Light-position state and movement, independent of terminal input/rendering."""

from dataclasses import dataclass

from nilavu.cells import line_width


@dataclass(frozen=True)
class LightPosition:
    """A zero-based position inside the document's rectangular bounds.

    x counts terminal columns; y counts source lines.
    max_x and max_y are inclusive bounds computed from prepared source text.
    The rectangle includes empty space beside short lines, allowing vertical
    movement to preserve the column. Empty documents still contain (0, 0).
    """

    max_x: int
    max_y: int
    x: int = 0
    y: int = 0

    def __post_init__(self) -> None:
        # Guard the invariant even when a caller constructs a position directly.
        if self.max_x < 0 or self.max_y < 0:
            raise ValueError("Document bounds must be nonnegative.")
        if not (0 <= self.x <= self.max_x and 0 <= self.y <= self.max_y):
            raise ValueError("Light position must be inside document bounds.")

    @classmethod
    def from_text(cls, source_text: str) -> "LightPosition":
        """Start at (0, 0), computing bounds once from normalized source text."""
        # Split only on the normalized newline, preserving blank lines and the
        # blank final row after a trailing newline. Empty text gives one row.
        lines = source_text.split("\n")
        # A line of width n has cell positions 0 through n - 1. Reserve
        # position zero even when every line is empty.
        max_x = max(0, max(line_width(line) for line in lines) - 1)
        return cls(max_x=max_x, max_y=len(lines) - 1)

    def move(self, dx: int, dy: int) -> "LightPosition":
        """Return a new position after applying and clamping coordinate offsets.

        A one-position movement uses offsets (1, 0), (-1, 0), (0, 1), or (0, -1).
        This layer works with offsets; a later UI step will map approved keys to
        those offsets. It never modifies source text or depends on a viewport.
        """
        # min caps the upper bound; max caps the lower bound. Apply each axis
        # independently so vertical movement never snaps x to a shorter line.
        x = max(0, min(self.max_x, self.x + dx))
        y = max(0, min(self.max_y, self.y + dy))
        # Immutable state makes each movement explicit and independently testable.
        return LightPosition(max_x=self.max_x, max_y=self.max_y, x=x, y=y)
