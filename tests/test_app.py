"""Integration checks for the minimal terminal viewer."""

from pathlib import Path
import tempfile
import unittest

from textual.geometry import Region
from textual.widgets import Static

from nilavu.app import NilavuApp
from nilavu.document import load_document
from nilavu.palette import DEFAULT_PALETTE


class NilavuAppTests(unittest.IsolatedAsyncioTestCase):
    async def test_displays_loaded_source_as_literal_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.py"
            path.write_bytes("\t[bold]நிலவு[/bold]\r\n\x1b[31mtext".encode("utf-8"))
            app = NilavuApp(load_document(path))

            # run_test mounts the real widgets without changing our terminal.
            async with app.run_test(size=(40, 5)):
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
        async with app.run_test(size=(20, 4)):
            source = app.query_one("#source", Static)
            # render_lines includes the padding drawn around empty content;
            # render_line alone describes the text before that padding.
            rows = source.render_lines(Region(0, 0, 20, 4))
            self.assertTrue(all(row.text == " " * 20 for row in rows))

    async def test_clips_long_lines_and_extra_rows_without_wrapping(self):
        app = NilavuApp("abcdefghijk\nsecond\nthird\nfourth")
        async with app.run_test(size=(8, 3)) as pilot:
            source = app.query_one("#source", Static)
            rows = source.render_lines(Region(0, 0, 8, 3))
            self.assertEqual(
                [row.text for row in rows], ["abcdefgh", "second  ", "third   "]
            )
            self.assertEqual(source.size.height, 3)

            # A resize changes visible bounds, without changing source content.
            await pilot.resize_terminal(5, 2)
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
