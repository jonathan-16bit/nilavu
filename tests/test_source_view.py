"""Check the playable key-to-state-to-lit-source interaction."""

import unittest

from nilavu.app import NilavuApp
from nilavu.palette import DEFAULT_PALETTE, SHADE_LEVELS
from nilavu.source_view import SourceView


def foregrounds(source: SourceView, row: int) -> list[tuple[int, int, int]]:
    """Expand rendered ASCII segments into a foreground color per character."""
    return [
        segment.style.color.triplet
        for segment in source.render_line(row)
        for _ in segment.text
    ]


def backgrounds(source: SourceView, row: int) -> list[tuple[int, int, int]]:
    """Expand rendered ASCII segments into a background color per cell."""
    return [
        segment.style.bgcolor.triplet
        for segment in source.render_line(row)
        for _ in segment.text
    ]


class SourceViewTests(unittest.IsolatedAsyncioTestCase):
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

    async def test_five_cell_shades_reach_darkness_at_radius_ten(self):
        app = NilavuApp("abcdefghijklmnopqrst")
        async with app.run_test(size=(25, 4)):
            source = app.query_one(SourceView)
            colors = foregrounds(source, 0)
            self.assertEqual(colors[1], DEFAULT_PALETTE.foreground)
            # Exclude the cursor at zero: the five levels descend in plateaus,
            # and each has a distinct matching cell background.
            greens = [color[1] for color in colors[1:11]]
            self.assertTrue(all(a >= b for a, b in zip(greens, greens[1:])))
            self.assertEqual(len(set(colors[1:11])), SHADE_LEVELS)
            cell_colors = backgrounds(source, 0)
            self.assertEqual(len(set(cell_colors[1:11])), SHADE_LEVELS)
            self.assertEqual(cell_colors[1], DEFAULT_PALETTE.cell_background)
            self.assertTrue(all(color == DEFAULT_PALETTE.background for color in cell_colors[10:]))
            self.assertTrue(all(color == DEFAULT_PALETTE.background for color in colors[10:]))
            self.assertEqual(source.render_line(0).text.rstrip(), "abcdefghijklmnopqrst")

    async def test_movement_relights_the_source_without_replacing_characters(self):
        app = NilavuApp("abcdefghijklmnopqrst\nABCDEFGHIJKLMNOPQRST")
        async with app.run_test(size=(25, 4)) as pilot:
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
        async with app.run_test(size=(12, 5)) as pilot:
            await pilot.press("right", "right", "right", "right", "right", "down")
            source = app.query_one(SourceView)
            self.assertEqual(source.render_line(1).text.rstrip(), "x")
            self.assertEqual(backgrounds(source, 1)[5], DEFAULT_PALETTE.cursor_background)
            await pilot.press("down")
            self.assertEqual(source.render_line(2).text, " " * 12)
            self.assertEqual(backgrounds(source, 2)[5], DEFAULT_PALETTE.cursor_background)
            self.assertEqual(backgrounds(source, 2)[6], DEFAULT_PALETTE.cell_background)
