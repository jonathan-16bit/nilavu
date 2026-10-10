"""Check the playable key-to-state-to-lit-source interaction."""

import unittest
from unittest.mock import patch

from rich.cells import cell_len

from nilavu.app import NilavuApp
from nilavu.lighting import LightSettings
from nilavu.palette import DEFAULT_PALETTE, SHADE_LEVELS
from nilavu.source_view import SourceView
from nilavu.viewport import Viewport
import nilavu.cells as cells_module


def foregrounds(source: SourceView, row: int) -> list[tuple[int, int, int]]:
    """Expand rendered segments into a foreground color per terminal cell."""
    return [
        segment.style.color.triplet
        for segment in source.render_line(row)
        for _ in range(cell_len(segment.text))
    ]


def backgrounds(source: SourceView, row: int) -> list[tuple[int, int, int]]:
    """Expand rendered segments into a background color per terminal cell."""
    return [
        segment.style.bgcolor.triplet
        for segment in source.render_line(row)
        for _ in range(cell_len(segment.text))
    ]


class SourceViewTests(unittest.IsolatedAsyncioTestCase):
    async def test_far_unicode_scroll_reuses_index_and_keeps_cursor_aligned(self):
        app = NilavuApp("a界e\u0301" * 20000)
        async with app.run_test(size=(42, 6)) as pilot:
            source = app.query_one(SourceView)
            app.action_move_light(79001, 0)
            await pilot.pause()
            with patch("nilavu.cells._glyph_at", wraps=cells_module._glyph_at) as read_glyph:
                content = source.render()
            self.assertLess(read_glyph.call_count, 400)
            self.assertEqual(cell_len(content.plain.split("\n")[0]), 40)
            cursor_x = app.light_position.x - source.viewport.x
            self.assertEqual(backgrounds(source, 0)[cursor_x], DEFAULT_PALETTE.cursor_background)
            # Starting inside a wide glyph produces a space, then the accent's
            # intact base; subsequent cells keep their original document columns.
            self.assertTrue(source.render_line(0).text.startswith(" e\u0301a界"))

    async def test_custom_geometry_drives_shading_scrolling_and_resize(self):
        settings = LightSettings(radius=4.5, cell_aspect_ratio=1.5)
        app = NilavuApp("\n".join(["a" * 50] * 30), light_settings=settings)
        async with app.run_test(size=(42, 22)) as pilot:
            source = app.query_one(SourceView)
            self.assertIs(source.light_settings, settings)
            self.assertEqual(backgrounds(source, 2)[0], backgrounds(source, 0)[3])
            self.assertEqual(backgrounds(source, 0)[5], DEFAULT_PALETTE.background)
            # The 4.5-column radius rounds to a five-column scrolling margin;
            # its three-row extent comes from the supplied ratio, not a default.
            app.action_move_light(35, 17)
            await pilot.pause()
            self.assertEqual(source.viewport, Viewport(1, 1))
            self.assertEqual(backgrounds(source, 16)[34], DEFAULT_PALETTE.cursor_background)
            await pilot.resize_terminal(32, 14)
            self.assertEqual(source.viewport, Viewport(11, 9))
            self.assertEqual(backgrounds(source, 8)[24], DEFAULT_PALETTE.cursor_background)

    async def test_cursor_covers_both_columns_of_wide_glyph_and_combining_base(self):
        app = NilavuApp("a界e\u0301z\nabcdef")
        async with app.run_test(size=(14, 6)) as pilot:
            source = app.query_one(SourceView)
            self.assertEqual(source.render_line(0).text.rstrip(), "a界e\u0301z")
            self.assertEqual(cell_len(source.render_line(0).text), 12)
            await pilot.press("right")
            self.assertEqual(backgrounds(source, 0)[1:3],
                             [DEFAULT_PALETTE.cursor_background] * 2)
            await pilot.press("right")
            self.assertEqual(backgrounds(source, 0)[1:3],
                             [DEFAULT_PALETTE.cursor_background] * 2)
            await pilot.press("right")
            self.assertEqual(backgrounds(source, 0)[3], DEFAULT_PALETTE.cursor_background)
            self.assertEqual(source.render_line(0).text.rstrip(), "a界e\u0301z")
            await pilot.press("down")
            self.assertEqual(backgrounds(source, 1)[3], DEFAULT_PALETTE.cursor_background)

    async def test_horizontal_scroll_clips_wide_glyph_without_shifting_following_text(self):
        app = NilavuApp("a界bcdefghijklmnop\nabcdefghijklmnopqr")
        async with app.run_test(size=(6, 5)) as pilot:
            source = app.query_one(SourceView)
            await pilot.press(*(["right"] * 4))
            self.assertEqual(source.viewport.x, 2)
            self.assertEqual(source.render_line(0).text, " bcd")
            self.assertEqual(cell_len(source.render_line(0).text), 4)
            self.assertEqual(backgrounds(source, 0)[2], DEFAULT_PALETTE.cursor_background)
            await pilot.press("left")
            self.assertEqual(source.viewport.x, 2)
            await pilot.press("left")
            self.assertEqual(source.viewport.x, 1)
            self.assertEqual(source.render_line(0).text, "界bc")
            self.assertEqual(backgrounds(source, 0)[:2],
                             [DEFAULT_PALETTE.cursor_background] * 2)

    async def test_scrolling_uses_full_light_radius_when_screen_has_room(self):
        lines = [f"{row:02}" + "abcdefghijklmnopqrstuvwxyz" * 2 for row in range(40)]
        app = NilavuApp("\n".join(lines))
        async with app.run_test(size=(32, 18)) as pilot:
            source = app.query_one(SourceView)
            await pilot.press(*(["right"] * 17 + ["down"] * 9))
            self.assertEqual(source.viewport, Viewport())
            await pilot.press("right", "down")
            # Scroll at the light's extents, well before the cursor reaches an edge.
            self.assertEqual(source.viewport, Viewport(1, 1))
            self.assertEqual(source.render_line(0).text, lines[1][1:31])
            self.assertEqual(backgrounds(source, 9)[17], DEFAULT_PALETTE.cursor_background)

    async def test_scrolling_keeps_source_cursor_and_light_aligned(self):
        lines = [f"{row:02}abcdefghijklmnop" for row in range(10)]
        app = NilavuApp("\n".join(lines))
        async with app.run_test(size=(10, 6)) as pilot:
            source = app.query_one(SourceView)
            await pilot.press(*(["right"] * 9 + ["down"] * 5))
            # Small screens reduce the radius margins instead of losing the cursor.
            self.assertEqual(source.viewport, Viewport(5, 3))
            self.assertEqual(source.render_line(0).text, lines[3][5:13])
            self.assertEqual(source.render_line(3).text, lines[6][5:13])
            self.assertEqual(backgrounds(source, 2)[4], DEFAULT_PALETTE.cursor_background)
            self.assertEqual(backgrounds(source, 2)[3], DEFAULT_PALETTE.cell_background)

            # Moving inside the visible area leaves the source stationary.
            await pilot.press("left", "up", "right", "down")
            self.assertEqual(source.viewport, Viewport(5, 3))
            self.assertEqual(backgrounds(source, 2)[4], DEFAULT_PALETTE.cursor_background)
            # Crossing the inset left and top edges reveals earlier source again.
            await pilot.press(*(["left"] * 7 + ["up"] * 3))
            self.assertEqual(source.viewport, Viewport(0, 1))
            self.assertEqual(source.render_line(0).text, lines[1][:8])
            self.assertEqual(backgrounds(source, 1)[2], DEFAULT_PALETTE.cursor_background)

    async def test_resize_follows_light_without_changing_document_position(self):
        app = NilavuApp("\n".join(["abcdefghijklmnopqrst"] * 10))
        async with app.run_test(size=(14, 8)) as pilot:
            source = app.query_one(SourceView)
            await pilot.press(*(["right"] * 9 + ["down"] * 5))
            await pilot.resize_terminal(7, 5)
            self.assertEqual((app.light_position.x, app.light_position.y), (9, 5))
            self.assertEqual(source.viewport, Viewport(7, 4))
            self.assertEqual(backgrounds(source, 1)[2], DEFAULT_PALETTE.cursor_background)
            await pilot.resize_terminal(27, 14)
            self.assertEqual(source.viewport, Viewport())
            self.assertEqual(backgrounds(source, 5)[9], DEFAULT_PALETTE.cursor_background)

    async def test_renderer_corrects_for_tall_terminal_cells(self):
        app = NilavuApp("\n".join(["abcdefghijklmnopqrst"] * 10))
        async with app.run_test(size=(27, 14)):
            source = app.query_one(SourceView)
            # Four columns and two rows represent the same visual distance at 2:1.
            self.assertEqual(backgrounds(source, 0)[4], backgrounds(source, 2)[0])
            self.assertEqual(backgrounds(source, 6)[0], DEFAULT_PALETTE.background)

    async def test_keys_move_the_light_and_clamp_at_document_edges(self):
        app = NilavuApp("abcdef\nx\n\nabcdef")
        async with app.run_test() as pilot:
            for key, expected in (
                ("h", (0, 0)), ("left", (0, 0)),
                ("k", (0, 0)), ("up", (0, 0)),
                ("l", (1, 0)), ("right", (2, 0)),
                ("j", (2, 1)), ("down", (2, 2)),
                ("down", (2, 3)), ("j", (2, 3)),
                ("k", (2, 2)), ("up", (2, 1)),
                ("h", (1, 1)), ("left", (0, 1)),
            ):
                with self.subTest(key=key, expected=expected):
                    await pilot.press(key)
                    self.assertEqual((app.light_position.x, app.light_position.y), expected)
            await pilot.press("right", "right", "right", "right", "right", "right")
            self.assertEqual(app.light_position.x, 5)

    async def test_five_cell_shades_reach_darkness_at_radius_twelve(self):
        app = NilavuApp("abcdefghijklmnopqrst")
        async with app.run_test(size=(27, 6)):
            source = app.query_one(SourceView)
            colors = foregrounds(source, 0)
            self.assertEqual(colors[1], DEFAULT_PALETTE.foreground)
            # Exclude the cursor at zero: the five levels descend in plateaus,
            # and each has a distinct matching cell background.
            greens = [color[1] for color in colors[1:13]]
            self.assertTrue(all(a >= b for a, b in zip(greens, greens[1:])))
            self.assertEqual(len(set(colors[1:13])), SHADE_LEVELS)
            cell_colors = backgrounds(source, 0)
            self.assertEqual(len(set(cell_colors[1:13])), SHADE_LEVELS)
            self.assertEqual(cell_colors[1], DEFAULT_PALETTE.cell_background)
            self.assertTrue(all(color == DEFAULT_PALETTE.background for color in cell_colors[12:]))
            self.assertTrue(all(color == DEFAULT_PALETTE.background for color in colors[12:]))
            self.assertEqual(source.render_line(0).text.rstrip(), "abcdefghijklmnopqrst")

    async def test_movement_relights_the_source_without_replacing_characters(self):
        app = NilavuApp("abcdefghijklmnopqrst\nABCDEFGHIJKLMNOPQRST")
        async with app.run_test(size=(27, 6)) as pilot:
            source = app.query_one(SourceView)
            before = foregrounds(source, 0)
            await pilot.press("l", "right", "l", "down")
            self.assertEqual(backgrounds(source, 1)[3], DEFAULT_PALETTE.cursor_background)
            self.assertNotEqual(backgrounds(source, 0)[0], DEFAULT_PALETTE.cursor_background)
            self.assertNotEqual(foregrounds(source, 0), before)
            self.assertEqual(source.render_line(0).text.rstrip(), "abcdefghijklmnopqrst")
            self.assertEqual(source.render_line(1).text.rstrip(), "ABCDEFGHIJKLMNOPQRST")
            await pilot.press("q")
            self.assertFalse(app.is_running)

    async def test_empty_document_remains_safe_under_movement(self):
        app = NilavuApp("")
        async with app.run_test() as pilot:
            await pilot.press("h", "j", "k", "l", "left", "down", "up", "right")
            self.assertEqual((app.light_position.x, app.light_position.y), (0, 0))
            self.assertEqual(backgrounds(app.query_one(SourceView), 0)[0], DEFAULT_PALETTE.cursor_background)
            await pilot.press("q")
            self.assertFalse(app.is_running)

    async def test_cursor_and_shading_remain_visible_on_short_and_blank_lines(self):
        app = NilavuApp("abcdef\nx\n\nabcdef")
        async with app.run_test(size=(14, 7)) as pilot:
            await pilot.press("right", "right", "right", "right", "right", "down")
            source = app.query_one(SourceView)
            self.assertEqual(source.render_line(1).text.rstrip(), "x")
            self.assertEqual(backgrounds(source, 1)[5], DEFAULT_PALETTE.cursor_background)
            await pilot.press("down")
            self.assertEqual(source.render_line(2).text, " " * 12)
            self.assertEqual(backgrounds(source, 2)[5], DEFAULT_PALETTE.cursor_background)
            self.assertEqual(backgrounds(source, 2)[6], DEFAULT_PALETTE.cell_background)
