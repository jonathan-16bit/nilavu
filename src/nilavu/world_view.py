"""Render fixed world terrain with the viewer's existing light and text cells."""

import math

from textual.content import Content, Span
from textual.message import Message

from nilavu.cells import visible_cells
from nilavu.companions import companion_glow
from nilavu.fireflies import Firefly, GLOW_RADIUS, sleeping_glow_frames
from nilavu.lighting import LightSettings, brightness_at
from nilavu.navigation import LightPosition
from nilavu.object_lighting import (
    ANIMATION_FRAMES, ANIMATION_INTERVAL, glow_field, water_highlight,
)
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
    Terrain.FLOWER: (91, 62, 81),
    Terrain.GOLD_FLOWER: (105, 96, 49),
    Terrain.MEADOW: (86, 100, 55),
    Terrain.TALL_GRASS: (58, 98, 59),
    Terrain.STONE: (60, 69, 85),
    Terrain.ROCK: (79, 92, 116),
    Terrain.CRYSTAL: (126, 76, 153),
    Terrain.STEPPING_STONE: (94, 104, 115),
    Terrain.RUIN: (114, 104, 88),
    Terrain.LANTERN: (139, 91, 40),
}


TERRAIN_FOREGROUNDS = {
    Terrain.MOSS: (127, 166, 100),
    Terrain.GRASS: (164, 193, 113),
    Terrain.EARTH: (177, 147, 99),
    Terrain.CANOPY: (108, 169, 111),
    Terrain.TRUNK: (224, 177, 113),
    Terrain.WATER: (115, 188, 218),
    Terrain.FLOWER: (241, 154, 202),
    Terrain.GOLD_FLOWER: (242, 215, 113),
    Terrain.MEADOW: (193, 213, 131),
    Terrain.TALL_GRASS: (146, 205, 124),
    Terrain.STONE: (167, 180, 207),
    Terrain.ROCK: (183, 201, 224),
    Terrain.CRYSTAL: (209, 164, 244),
    Terrain.STEPPING_STONE: (211, 220, 232),
    Terrain.RUIN: (217, 202, 174),
    Terrain.LANTERN: (255, 224, 133),
}


class WorldView(SourceView):
    """A bounded world viewport; its widget border separates it from extra space."""

    class AnimationTick(Message):
        """Let the game gather companions using the existing scenery clock."""

    def __init__(self, world: World, light: LightPosition, palette: Palette,
                 *, light_settings: LightSettings, reveal: bool = False,
                 fireflies: tuple[Firefly, ...] = ()) -> None:
        super().__init__(world.text, light, palette, light_settings=light_settings)
        self.world = world
        self._glows = glow_field(world, light_settings.cell_aspect_ratio)
        self._cache_animation()
        self.fireflies = fireflies
        self.companion_positions = ()
        self._companion_light = {}
        self._cache_fireflies()
        self.reveal = reveal
        self.add_class("game-world")
        self.styles.width = world.width + 2
        self.styles.height = world.height + 2
        self.update_palette(palette)

    def _cache_fireflies(self) -> None:
        self._firefly_frames = tuple(
            sleeping_glow_frames(self.world, fly.position, self.light_settings.cell_aspect_ratio)
            for fly in self.fireflies
        )

    def update_fireflies(self, fireflies: tuple[Firefly, ...]) -> None:
        self.fireflies = fireflies
        self._cache_fireflies()
        self.update_palette(self.palette)

    def update_companions(self, positions: tuple[tuple[int, int], ...]) -> None:
        if positions != self.companion_positions:
            self.companion_positions = positions
            self._companion_light = companion_glow(
                self.world, positions, self.light_settings.cell_aspect_ratio)
            self.refresh()

    def _cache_animation(self) -> None:
        # Precompute the small loop once per world. The timer only selects a
        # frame; it never regenerates terrain or recalculates light distances.
        self._glow_frames = tuple(
            glow_field(self.world, self.light_settings.cell_aspect_ratio, frame=frame)
            for frame in range(ANIMATION_FRAMES)
        )
        self._animation_frame = 0

    def on_mount(self) -> None:
        self._animation_timer = self.set_interval(ANIMATION_INTERVAL, self._advance_animation)

    def on_unmount(self) -> None:
        self._animation_timer.stop()

    def _advance_animation(self) -> None:
        self._animation_frame = (self._animation_frame + 1) % ANIMATION_FRAMES
        self.post_message(self.AnimationTick())
        self.refresh()

    def update_palette(self, palette: Palette) -> None:
        self.palette = palette
        # Cache per-cell color roles only on world/theme changes. Cursor movement
        # chooses one of the same five shades, without rebuilding terrain colors.
        def mix(first, second, amount):
            return tuple(round(a + (b - a) * amount) for a, b in zip(first, second))

        def shift(rgb, amount):
            return tuple(max(0, min(255, c + amount)) for c in rgb)

        palettes = []
        self._water_palettes = {}
        self._dim_accent_palettes = {}
        for y, row in enumerate(self.world.terrain):
            colors = []
            for x, kind in enumerate(row):
                fg, bg = TERRAIN_FOREGROUNDS[kind], TERRAIN_COLORS[kind]
                # Broad quiet variation on ground; directional highlights on
                # foliage, stone, and water keep objects from looking flat.
                if kind in (Terrain.CANOPY, Terrain.ROCK, Terrain.RUIN):
                    above = self.world.terrain[y - 1][x] if y else None
                    delta = 12 if above != kind else -4
                else:
                    delta = (((x // 8) * 17 + (y // 4) * 13) % 3 - 1) * 4
                fg, bg = shift(fg, delta), shift(bg, delta)
                if kind in (Terrain.FLOWER, Terrain.GOLD_FLOWER) and self.world.lines[y][x] == "*":
                    fg = (255, 223, 166)  # Small warm centers contrast with petals.
                if kind == Terrain.WATER:
                    fg = (151, 218, 236)
                    bg = (bg[0], bg[1] + 7, bg[2] + 12)
                fg = mix(fg, palette.foreground, 0.20)
                bg = mix(bg, palette.cell_background, 0.20)
                glow = self._glows[y][x]
                fg = mix(fg, glow.color, glow.brightness * 0.35)
                bg = mix(bg, glow.color, glow.brightness * 0.18)
                cell_palette = Palette(background=palette.background, foreground=fg,
                                       cell_background=bg, cursor_background=palette.cursor_background)
                colors.append(cell_palette)
                if kind in (Terrain.CRYSTAL, Terrain.LANTERN):
                    # A small text-color shift also shows the pulse under full
                    # cursor illumination or in the fully revealed preview.
                    self._dim_accent_palettes[x, y] = Palette(
                        background=palette.background, foreground=shift(fg, -12),
                        cell_background=bg, cursor_background=palette.cursor_background,
                    )
                if kind == Terrain.WATER:
                    self._water_palettes[x, y] = Palette(
                        background=palette.background,
                        foreground=mix(fg, (215, 239, 247), 0.18),
                        cell_background=mix(bg, (98, 167, 196), 0.08),
                        cursor_background=palette.cursor_background,
                    )
            palettes.append(tuple(colors))
        self._cell_palettes = tuple(palettes)
        self._firefly_palette = Palette(
            background=palette.background, foreground=(255, 255, 255),
            cell_background=(50, 66, 58), cursor_background=palette.cursor_background,
        )
        # Only the small halo areas need extra color roles; terrain remains intact.
        halo_cells = {cell for frames in self._firefly_frames for frame in frames for cell in frame}
        self._firefly_palettes = {}
        for x, y in halo_cells:
            cell = self._cell_palettes[y][x]
            self._firefly_palettes[x, y] = Palette(
                background=palette.background,
                foreground=mix(cell.foreground, (236, 247, 255), 0.20),
                cell_background=mix(cell.cell_background, (117, 139, 145), 0.20),
                cursor_background=palette.cursor_background,
            )
        self._companion_palette = Palette(
            background=palette.background, foreground=(255, 246, 194),
            cell_background=(63, 66, 46), cursor_background=palette.cursor_background,
        )
        roles = {cell for row in self._cell_palettes for cell in row}
        roles.update(self._water_palettes.values())
        roles.update(self._dim_accent_palettes.values())
        self._companion_palettes = {
            cell: Palette(background=palette.background,
                          foreground=mix(cell.foreground, (255, 246, 194), 0.20),
                          cell_background=mix(cell.cell_background, (130, 120, 68), 0.20),
                          cursor_background=palette.cursor_background)
            for cell in roles
        }
        self.refresh()

    def update_world(self, world: World, light: LightPosition) -> None:
        self.world = world
        self.fireflies = ()
        self.companion_positions = ()
        self._companion_light = {}
        self._cache_fireflies()
        self._glows = glow_field(world, self.light_settings.cell_aspect_ratio)
        self._cache_animation()
        self.update_palette(self.palette)
        self._lines = list(world.lines)
        self._cell_indexes = {}
        self.viewport = Viewport()
        self.update_light(light)

    def render(self) -> Content:
        # Textual can draw the new size before delivering its Resize event.
        # Clamp the viewport now too, so an old scroll origin cannot overrun it.
        self._follow_light(self.size.width, self.size.height)
        firefly_cells = set()
        companion_cells = set(self.companion_positions)
        cursor_cell = (self.light_position.x, self.light_position.y)
        firefly_light = {}
        for fly, frames in zip(self.fireflies, self._firefly_frames):
            distance = math.hypot(fly.position[0] - self.light_position.x,
                                  (fly.position[1] - self.light_position.y)
                                  * self.light_settings.cell_aspect_ratio)
            if fly.awake or (not self.reveal and distance > self.light_settings.radius + GLOW_RADIUS):
                continue
            firefly_cells.add(fly.position)
            for cell, intensity in frames[self._animation_frame].items():
                firefly_light[cell] = max(firefly_light.get(cell, 0), intensity)
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
                kind = self.world.terrain[y][x]
                glow = self._glow_frames[self._animation_frame][y][x]
                intensity = max(intensity, glow.brightness)
                palette = self._cell_palettes[y][x]
                if kind == Terrain.WATER and water_highlight(x, y, self._animation_frame):
                    palette = self._water_palettes[x, y]
                elif kind in (Terrain.CRYSTAL, Terrain.LANTERN) and glow.level < self._glows[y][x].level:
                    palette = self._dim_accent_palettes[x, y]
                companion_light = self._companion_light.get((x, y), 0)
                if companion_light:
                    intensity = max(intensity, companion_light)
                    palette = self._companion_palettes[palette]
                nearby_glow = firefly_light.get((x, y), 0)
                if nearby_glow > intensity:
                    intensity = nearby_glow
                    palette = self._firefly_palettes[x, y]
                if (x, y) in firefly_cells:
                    glyph = "i"
                    palette = self._firefly_palette
                    # The body stays readable while its small halo pulses.
                    intensity = 1.0
                elif (x, y) in companion_cells and (x, y) != cursor_cell and glyph == " ":
                    glyph = "i"
                    palette = self._companion_palette
                    intensity = 1.0
                style = palette.style_at(intensity)
                # Keep foliage light; reserve heavier text for small accents.
                if (kind in (Terrain.TRUNK, Terrain.CRYSTAL, Terrain.LANTERN)
                        or (x, y) in firefly_cells or ((x, y) in companion_cells and glyph == "i")):
                    style += " bold"
                if y == self.light_position.y and x <= self.light_position.x < x + cells:
                    style = self.palette.cursor_style()
                spans.append(Span(offset, offset + len(glyph), style))
                offset += len(glyph)
                parts.append(glyph)
            lines.append("".join(parts))
            offset += 1
        return Content("\n".join(lines), spans=spans)
