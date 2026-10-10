"""Integration checks for the minimal terminal viewer."""

from pathlib import Path
import tempfile
import unittest

from textual.geometry import Region
from textual.containers import Container
from textual.widgets import Static

from nilavu.app import NilavuApp
from nilavu.document import load_document
from nilavu.palette import DEFAULT_PALETTE
from nilavu.source_view import SourceView


class NilavuAppTests(unittest.IsolatedAsyncioTestCase):
    async def test_border_uses_terminal_default_foreground_and_resizes(self):
        app = NilavuApp("abc")
        async with app.run_test(size=(12, 6)) as pilot:
            frame = app.query_one("#frame", Container)
            source = app.query_one(SourceView)
            self.assertEqual(source.region, Region(1, 1, 10, 4))
            rows = frame.render_lines(Region(0, 0, 12, 6))
            self.assertEqual(rows[0].text, "┌" + "─" * 10 + "┐")
            self.assertEqual(rows[-1].text, "└" + "─" * 10 + "┘")
            # The emitted border style must remain terminal-default color,
            # rather than being resolved to the app's green or a fixed RGB value.
            self.assertTrue(all(segment.style.color.is_default for segment in rows[0]))
            self.assertTrue(all(segment.style.bgcolor.is_default for segment in rows[0]))
            await pilot.resize_terminal(18, 8)
            self.assertEqual(source.region, Region(1, 1, 16, 6))
            rows = frame.render_lines(Region(0, 0, 18, 8))
            self.assertEqual(rows[0].text, "┌" + "─" * 16 + "┐")
            self.assertTrue(all(segment.style.color.is_default for segment in rows[0]))
            self.assertTrue(all(segment.style.bgcolor.is_default for segment in rows[0]))

    async def test_tiny_border_interior_follows_cursor_and_clipped_frame_exits(self):
        app = NilavuApp("abc\ndef")
        async with app.run_test(size=(3, 3)) as pilot:
            source = app.query_one(SourceView)
            await pilot.press("right", "right", "down")
            self.assertEqual(source.region, Region(1, 1, 1, 1))
            self.assertEqual((source.viewport.x, source.viewport.y), (2, 1))
            self.assertEqual(source.render_line(0).text, "f")
            self.assertEqual(next(iter(source.render_line(0))).style.bgcolor.triplet,
                             DEFAULT_PALETTE.cursor_background)
            await pilot.resize_terminal(1, 1)
            # Below the border's minimum size, Textual clips the frame. Input
            # must still work even when there is no visible source area.
            self.assertEqual((app.size.width, app.size.height), (1, 1))
            await pilot.press("q")
            self.assertFalse(app.is_running)

    async def test_displays_loaded_source_as_literal_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.py"
            path.write_bytes("\t[bold]நிலவு[/bold]\r\n\x1b[31mtext".encode("utf-8"))
            app = NilavuApp(load_document(path))

            # run_test mounts the real widgets without changing our terminal.
            async with app.run_test(size=(42, 7)):
                source = app.query_one("#source", Static)
                self.assertEqual(
                    source.render_line(0).text.rstrip(), "    [bold]நிலவு[/bold]"
                )
                self.assertEqual(source.render_line(1).text.rstrip(), r"\x1b[31mtext")
                # The approved palette must survive the rendering pipeline.
                style = next(iter(source.render_line(0))).style
                self.assertEqual(style.color.triplet, DEFAULT_PALETTE.background)
                self.assertEqual(style.bgcolor.triplet, DEFAULT_PALETTE.cursor_background)

    async def test_empty_document_starts_with_a_blank_screen(self):
        app = NilavuApp("")
        async with app.run_test(size=(22, 6)):
            source = app.query_one("#source", Static)
            # render_lines includes the padding drawn around empty content;
            # render_line alone describes the text before that padding.
            rows = source.render_lines(Region(0, 0, 20, 4))
            self.assertTrue(all(row.text == " " * 20 for row in rows))

    async def test_clips_long_lines_and_extra_rows_without_wrapping(self):
        app = NilavuApp("abcdefghijk\nsecond\nthird\nfourth")
        async with app.run_test(size=(10, 5)) as pilot:
            source = app.query_one("#source", Static)
            rows = source.render_lines(Region(0, 0, 8, 3))
            self.assertEqual(
                [row.text for row in rows], ["abcdefgh", "second  ", "third   "]
            )
            self.assertEqual(source.size.height, 3)

            # A resize changes visible bounds, without changing source content.
            await pilot.resize_terminal(7, 4)
            self.assertEqual(source.render_line(0).text, "abcde")
            self.assertEqual(source.render_line(1).text, "secon")
            self.assertEqual(source.size.height, 2)

    async def test_q_exits_the_app(self):
        app = NilavuApp("source")
        async with app.run_test() as pilot:
            await pilot.press("q")
            # Assert before leaving run_test: its cleanup also stops the app,
            # which would otherwise hide a broken quit binding.
            self.assertFalse(app.is_running)
        self.assertEqual(app.return_code, 0)
