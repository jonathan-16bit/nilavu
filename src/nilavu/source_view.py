"""Apply lighting to visible source characters at the Textual UI boundary."""

from textual.content import Content, Span
from textual.widgets import Static

from nilavu.lighting import brightness_at
from nilavu.navigation import LightPosition
from nilavu.palette import DEFAULT_PALETTE, Palette


LIGHT_RADIUS = 10.0


class SourceView(Static):
    """Render prepared source text using a supplied light position and palette."""

    def __init__(
        self,
        source_text: str,
        light_position: LightPosition,
        palette: Palette = DEFAULT_PALETTE,
    ) -> None:
        super().__init__(id="source", markup=False)
        # The document is split once. Movement changes only light state, never
        # file contents, and rendering work is limited to the visible rectangle.
        self._lines = source_text.split("\n")
        self.light_position = light_position
        self.palette = palette

    def render(self) -> Content:
        """Return actual source characters with foreground-color spans."""
        lines = [line[: self.size.width] for line in self._lines[: self.size.height]]
        spans = []
        offset = 0
        for y, line in enumerate(lines):
            for x, _ in enumerate(line):
                intensity = brightness_at(
                    x, y, self.light_position.x, self.light_position.y, LIGHT_RADIUS
                )
                color = self.palette.color_at(intensity)
                # A span styles one character in the combined text. Newlines
                # occupy a string position too, so each row advances by len + 1.
                spans.append(Span(offset + x, offset + x + 1, color))
            offset += len(line) + 1
        # Content receives literal text, not parsed markup. Dark characters remain
        # source characters; their foreground matches the approved background.
        # Coordinates still count Python characters; terminal-cell width handling
        # for wide/combining Unicode is a separate concern from this light layer.
        return Content("\n".join(lines), spans=spans)
