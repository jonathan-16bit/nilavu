"""Render fixed world terrain with the viewer's existing light and text cells."""

from textual.content import Content, Span

from nilavu.cells import visible_cells
from nilavu.lighting import LightSettings, brightness_at
from nilavu.navigation import LightPosition
from nilavu.palette import Palette
from nilavu.source_view import SourceView
from nilavu.viewport import Viewport
from nilavu.world import Terrain, World

# These roles identify terrain; blending in the chosen palette keeps its colors
# coordinated. All roles share darkness and the same five lighting levels.
TERRAIN_COLORS = {
    Terrain.MOSS: (43, 75, 44),
    Terrain.GRASS: (61, 92, 47),
    Terrain.EARTH: (75, 78, 60),  # Muted ground stays separate from warm wood.
    Terrain.CANOPY: (28, 58, 37),
    Terrain.TRUNK: (122, 63, 36),
    Terrain.WATER: (34, 82, 113),
    Terrain.FLOWER: (43, 75, 44),
}


TERRAIN_FOREGROUNDS = {
    Terrain.MOSS: (127, 166, 100),
    Terrain.GRASS: (164, 193, 113),
    Terrain.EARTH: (177, 147, 99),
    Terrain.CANOPY: (108, 169, 111),
    Terrain.TRUNK: (224, 177, 113),
    Terrain.WATER: (115, 188, 218),
    Terrain.FLOWER: (228, 158, 195),
}


class WorldView(SourceView):
    """A bounded world viewport; its widget border separates it from extra space."""

    def __init__(self, world: World, light: LightPosition, palette: Palette,
                 *, light_settings: LightSettings, reveal: bool = False) -> None:
        super().__init__(world.text, light, palette, light_settings=light_settings)
        self.world = world
        self.reveal = reveal
        self.add_class("game-world")
        self.styles.width = world.width + 2
        self.styles.height = world.height + 2
        self.update_palette(palette)

    def update_palette(self, palette: Palette) -> None:
        self.palette = palette
        self._terrain_palettes = {
            kind: Palette(
                background=palette.background,
                foreground=tuple((3 * color + tint) // 4 for color, tint in
                                 zip(TERRAIN_FOREGROUNDS[kind], palette.foreground)),
                cell_background=tuple((3 * color + tint) // 4
                                      for color, tint in zip(rgb, palette.cell_background)),
                cursor_background=palette.cursor_background,
            ) for kind, rgb in TERRAIN_COLORS.items()
        }
        self.refresh()

    def update_world(self, world: World, light: LightPosition) -> None:
        self.world = world
        self._lines = list(world.lines)
        self._cell_indexes = {}
        self.viewport = Viewport()
        self.update_light(light)

    def render(self) -> Content:
        # Textual can draw the new size before delivering its Resize event.
        # Clamp the viewport now too, so an old scroll origin cannot overrun it.
        self._follow_light(self.size.width, self.size.height)
        lines, spans = [], []
        offset = 0
        for y in range(self.viewport.y, self.viewport.y + self.size.height):
            parts = []
            for x, glyph, cells in visible_cells(self.world.lines[y], self.viewport.x,
                                                  self.size.width):
                intensity = 1.0 if self.reveal else brightness_at(
                    x, y, self.light_position.x, self.light_position.y,
                    self.light_settings.radius,
                    cell_aspect_ratio=self.light_settings.cell_aspect_ratio)
                style = self._terrain_palettes[self.world.terrain[y][x]].style_at(intensity)
                if y == self.light_position.y and x <= self.light_position.x < x + cells:
                    style = self.palette.cursor_style()
                spans.append(Span(offset, offset + len(glyph), style))
                offset += len(glyph)
                parts.append(glyph)
            lines.append("".join(parts))
            offset += 1
        return Content("\n".join(lines), spans=spans)
