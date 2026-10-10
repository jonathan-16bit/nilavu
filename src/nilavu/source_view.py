"""Apply lighting to visible source characters at the Textual UI boundary."""

from textual.content import Content, Span
from textual.events import Resize
from textual.widgets import Static

from nilavu.lighting import brightness_at
from nilavu.navigation import LightPosition
from nilavu.palette import DEFAULT_PALETTE, Palette
from nilavu.viewport import Viewport


# Radius in column-width units; tune the light's reach independently of its shape.
LIGHT_RADIUS = 12.0
# Cell height / width. Keep this visual estimate explicit and easy to tune after
# trying the light with different fonts; it is not a universal terminal constant.
CELL_ASPECT_RATIO = 2.0


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
        self.viewport = Viewport()

    def update_light(self, position: LightPosition) -> None:
        """Follow document movement, then let Textual schedule the new frame."""
        self.light_position = position
        self.viewport = self.viewport.follow(position, self.size.width, self.size.height)
        self.refresh()

    def on_resize(self, event: Resize) -> None:
        """Keep the light visible when the terminal's visible area changes."""
        self.viewport = self.viewport.follow(
            self.light_position, event.size.width, event.size.height
        )
        self.refresh()

    def render(self) -> Content:
        """Return source characters with stepped cell shading and a cursor."""
        # Pad the visible rectangle with spaces, as a terminal already does.
        # Styling those cells makes the light and cursor visible on blank lines.
        lines = [
            (self._lines[y] if y < len(self._lines) else "")
            [self.viewport.x : self.viewport.x + self.size.width].ljust(self.size.width)
            for y in range(self.viewport.y, self.viewport.y + self.size.height)
        ]
        spans = []
        offset = 0
        for y, line in enumerate(lines):
            for x, _ in enumerate(line):
                # Screen positions change while scrolling; light and source
                # positions stay in document space so their shading stays aligned.
                document_x = x + self.viewport.x
                document_y = y + self.viewport.y
                intensity = brightness_at(
                    document_x,
                    document_y,
                    self.light_position.x,
                    self.light_position.y,
                    LIGHT_RADIUS,
                    cell_aspect_ratio=CELL_ASPECT_RATIO,
                )
                style = self.palette.style_at(intensity)
                # Apply the cursor last so it stays distinct from every shade.
                # The original character (including a space) stays underneath.
                if (document_x, document_y) == (self.light_position.x, self.light_position.y):
                    style = self.palette.cursor_style()
                # A span styles one character in the combined text. Newlines
                # occupy a string position too, so each row advances by len + 1.
                spans.append(Span(offset + x, offset + x + 1, style))
            offset += len(line) + 1
        # Content receives literal text, not parsed markup. Dark characters remain
        # source characters; their foreground matches the approved background.
        # Coordinates still count Python characters; terminal-cell width handling
        # for wide/combining Unicode is a separate concern from this light layer.
        return Content("\n".join(lines), spans=spans)
