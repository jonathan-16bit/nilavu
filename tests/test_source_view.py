"""Check the playable key-to-state-to-lit-source interaction."""

import unittest

from nilavu.app import NilavuApp
from nilavu.palette import DEFAULT_PALETTE
from nilavu.source_view import SourceView


def foregrounds(source: SourceView, row: int) -> list[tuple[int, int, int]]:
    """Expand rendered ASCII segments into a foreground color per character."""
    return [
        segment.style.color.triplet
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

    async def test_foreground_fades_to_background_at_radius_ten(self):
        app = NilavuApp("abcdefghijklmnopqrst")
        async with app.run_test(size=(25, 4)):
            source = app.query_one(SourceView)
            colors = foregrounds(source, 0)
            self.assertEqual(colors[0], DEFAULT_PALETTE.foreground)
            # Green-channel brightness decreases smoothly, rather than using a
            # handful of fixed bands. At and beyond the radius text is dark.
            greens = [color[1] for color in colors[:11]]
            self.assertTrue(all(a > b for a, b in zip(greens, greens[1:])))
            self.assertTrue(all(color == DEFAULT_PALETTE.background for color in colors[10:]))
            self.assertEqual(source.render_line(0).text, "abcdefghijklmnopqrst")

    async def test_movement_relights_the_source_without_replacing_characters(self):
        app = NilavuApp("abcdefghijklmnopqrst\nABCDEFGHIJKLMNOPQRST")
        async with app.run_test(size=(25, 4)) as pilot:
            source = app.query_one(SourceView)
            before = foregrounds(source, 0)
            await pilot.press("l", "right", "l", "down")
            self.assertEqual(foregrounds(source, 1)[3], DEFAULT_PALETTE.foreground)
            self.assertNotEqual(foregrounds(source, 0), before)
            self.assertEqual(source.render_line(0).text, "abcdefghijklmnopqrst")
            self.assertEqual(source.render_line(1).text, "ABCDEFGHIJKLMNOPQRST")
            await pilot.press("q")
            self.assertFalse(app.is_running)

    async def test_empty_document_remains_safe_under_movement(self):
        app = NilavuApp("")
        async with app.run_test() as pilot:
            await pilot.press("h", "j", "k", "l", "left", "down", "up", "right")
            self.assertEqual((app.light_position.x, app.light_position.y), (0, 0))
            await pilot.press("q")
            self.assertFalse(app.is_running)
