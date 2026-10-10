"""Apply lighting to visible source characters at the Textual UI boundary."""

import math

from textual.content import Content, Span
from textual.events import Resize
from textual.widgets import Static

from nilavu.cells import visible_cells
from nilavu.lighting import DEFAULT_LIGHT_SETTINGS, LightSettings, brightness_at
from nilavu.navigation import LightPosition
from nilavu.palette import DEFAULT_PALETTE, Palette
from nilavu.viewport import Viewport


class SourceView(Static):
    """Render prepared source text using a supplied light position and palette."""

    def __init__(
        self,
        source_text: str,
        light_position: LightPosition,
        palette: Palette = DEFAULT_PALETTE,
        *,
        light_settings: LightSettings = DEFAULT_LIGHT_SETTINGS,
    ) -> None:
        super().__init__(id="source", markup=False)
        # The document is split once. Movement changes only light state, never
        # file contents, and rendering work is limited to the visible rectangle.
        self._lines = source_text.split("\n")
        self.light_position = light_position
        self.palette = palette
        self.light_settings = light_settings
        self.viewport = Viewport()

    def update_light(self, position: LightPosition) -> None:
        """Follow document movement, then let Textual schedule the new frame."""
        self.light_position = position
        self._follow_light(self.size.width, self.size.height)
        self.refresh()

    def on_resize(self, event: Resize) -> None:
        """Keep the light visible when the terminal's visible area changes."""
        self._follow_light(event.size.width, event.size.height)
        self.refresh()

    def _follow_light(self, width: int, height: int) -> None:
        # The same geometry drives shading and scrolling. Round fractional cell
        # extents up to reserve space for the outer light when the screen fits it.
        self.viewport = self.viewport.follow(
            self.light_position,
            width,
            height,
            margin_x=math.ceil(self.light_settings.radius),
            margin_y=math.ceil(
                self.light_settings.radius / self.light_settings.cell_aspect_ratio
            ),
        )

    def render(self) -> Content:
        """Return source characters with stepped cell shading and a cursor."""
        # Pad the visible rectangle with spaces, as a terminal already does.
        # Styling those cells makes the light and cursor visible on blank lines.
        lines = []
        spans = []
        offset = 0
        for document_y in range(self.viewport.y, self.viewport.y + self.size.height):
            text = self._lines[document_y] if document_y < len(self._lines) else ""
            parts = []
            for document_x, glyph, cells in visible_cells(
                text, self.viewport.x, self.size.width
            ):
                intensity = brightness_at(
                    document_x,
                    document_y,
                    self.light_position.x,
                    self.light_position.y,
                    self.light_settings.radius,
                    cell_aspect_ratio=self.light_settings.cell_aspect_ratio,
                )
                style = self.palette.style_at(intensity)
                # Apply the cursor last so it stays distinct from every shade.
                # The original character (including a space) stays underneath.
                if (
                    document_y == self.light_position.y
                    and document_x <= self.light_position.x < document_x + cells
                ):
                    style = self.palette.cursor_style()
                # Styles use string indices, while lighting uses terminal columns.
                # Keep combining marks in the same span as their base glyph.
                spans.append(Span(offset, offset + len(glyph), style))
                offset += len(glyph)
                parts.append(glyph)
            lines.append("".join(parts))
            offset += 1  # The newline also occupies a string index.
        # Content receives literal text, not parsed markup. Dark characters remain
        # source characters; their foreground matches the approved background.
        return Content("\n".join(lines), spans=spans)
