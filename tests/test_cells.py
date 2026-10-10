"""Protect cell accounting and clipping without starting the terminal UI."""

import unittest
from unittest.mock import patch

from rich.cells import cell_len

from nilavu.cells import CellIndex, line_width, visible_cells
import nilavu.cells as cells_module


class CellTests(unittest.TestCase):
    def test_far_ascii_view_does_not_measure_the_hidden_prefix(self):
        text = "a" * (1024 * 1024 - 4) + "tail"
        with patch("nilavu.cells.get_character_cell_size", side_effect=AssertionError(
            "ASCII seeking should not scan glyphs"
        )):
            cells = list(visible_cells(text, len(text) - 4, 6))
        self.assertEqual("".join(glyph for _, glyph, _ in cells), "tail  ")

    def test_unicode_index_preserves_clipping_marks_and_padding(self):
        text = "\u0301" + "a界e\u0301✈\ufe0f" * 1000 + "tail"
        index = CellIndex(text)
        for start in (0, 1, 2, 255, 256, 257, 5999, 6000, 6004, 6010):
            for width in (0, 1, 2, 7):
                with self.subTest(start=start, width=width):
                    self.assertEqual(list(index.visible_cells(start, width)),
                                     list(visible_cells(text, start, width)))

    def test_far_unicode_view_reads_only_nearby_glyphs(self):
        index = CellIndex("a界e\u0301" * 20000)
        with patch("nilavu.cells._glyph_at", wraps=cells_module._glyph_at) as read_glyph:
            cells = list(index.visible_cells(79001, 80))
        self.assertEqual(sum(width for _, _, width in cells), 80)
        # Count work instead of elapsed time: this fails if seeking ever reverts
        # to scanning tens of thousands of hidden glyphs on every frame.
        self.assertLess(read_glyph.call_count, 400)

    def test_width_matches_visible_cells_for_mixed_text(self):
        for text in ("", "abc", "界e\u0301🙂", "\u0301a", "✈\ufe0fX"):
            with self.subTest(text=text):
                width = line_width(text)
                cells = list(visible_cells(text, 0, width))
                self.assertEqual(sum(size for _, _, size in cells), width)
                self.assertEqual(cell_len("".join(glyph for _, glyph, _ in cells)), width)

    def test_combining_marks_share_the_base_glyph(self):
        self.assertEqual(list(visible_cells("ae\u0301\u0308界", 0, 4)),
                         [(0, "a", 1), (1, "e\u0301\u0308", 1), (2, "界", 2)])

    def test_clipping_either_half_of_wide_glyph_uses_a_space(self):
        self.assertEqual(list(visible_cells("a界b", 0, 2)), [(0, "a", 1), (1, " ", 1)])
        self.assertEqual(list(visible_cells("a界b", 2, 2)), [(2, " ", 1), (3, "b", 1)])
        self.assertEqual(list(visible_cells("a界b", 1, 2)), [(1, "界", 2)])

    def test_padding_and_scroll_beyond_short_line_use_document_columns(self):
        self.assertEqual(list(visible_cells("界", 3, 2)), [(3, " ", 1), (4, " ", 1)])
        self.assertEqual(list(visible_cells("", 0, 2)), [(0, " ", 1), (1, " ", 1)])

    def test_leading_marks_get_a_display_base_space(self):
        self.assertEqual(list(visible_cells("\u0301\u0308a", 0, 2)),
                         [(0, " \u0301\u0308", 1), (1, "a", 1)])

    def test_zero_width_view_yields_no_text(self):
        self.assertEqual(list(visible_cells("界e\u0301", 0, 0)), [])
