"""Check document-space movement without launching a terminal application."""

import unittest

from nilavu.document import normalize_text
from nilavu.navigation import LightPosition


class LightPositionTests(unittest.TestCase):
    def test_starts_at_top_left_with_bounds_from_the_longest_line(self):
        position = LightPosition.from_text("ab\nlongest\nx")
        self.assertEqual((position.x, position.y), (0, 0))
        self.assertEqual((position.max_x, position.max_y), (6, 2))

    def test_moves_one_position_in_each_direction(self):
        center = LightPosition(max_x=4, max_y=4, x=2, y=2)
        for dx, dy, expected in (
            (1, 0, (3, 2)),
            (-1, 0, (1, 2)),
            (0, 1, (2, 3)),
            (0, -1, (2, 1)),
        ):
            with self.subTest(dx=dx, dy=dy):
                moved = center.move(dx, dy)
                self.assertEqual((moved.x, moved.y), expected)
        # Movement produces new state; the original remains reusable.
        self.assertEqual((center.x, center.y), (2, 2))

    def test_clamps_movement_at_all_four_edges(self):
        position = LightPosition.from_text("abc\ndef")
        for dx, dy, expected in (
            (-1, 0, (0, 0)),
            (0, -1, (0, 0)),
            (100, 0, (2, 0)),
            (0, 100, (0, 1)),
            (100, 100, (2, 1)),
        ):
            with self.subTest(dx=dx, dy=dy):
                moved = position.move(dx, dy)
                self.assertEqual((moved.x, moved.y), expected)
        bottom_right = position.move(100, 100)
        self.assertEqual(bottom_right.move(1, 1), bottom_right)
        self.assertEqual(bottom_right.move(-100, -100), position)

    def test_preserves_column_across_short_and_blank_lines(self):
        position = LightPosition.from_text("abcdef\nx\n\nabcdef").move(5, 0)
        for expected_y in (1, 2, 3):
            position = position.move(0, 1)
            self.assertEqual((position.x, position.y), (5, expected_y))
        # The document-wide width also permits horizontal movement on a blank row.
        position = position.move(0, -1).move(-1, 0)
        self.assertEqual((position.x, position.y), (4, 2))

    def test_empty_text_has_one_valid_position(self):
        position = LightPosition.from_text("")
        self.assertEqual((position.max_x, position.max_y), (0, 0))
        self.assertEqual(position.move(10, 10), position)
        self.assertEqual(position.move(-10, -10), position)

    def test_blank_lines_and_trailing_newline_remain_rows(self):
        for text, max_y in (("\n\n", 2), ("abc\n", 1), ("abc\n\n", 2)):
            with self.subTest(text=text):
                position = LightPosition.from_text(text)
                self.assertEqual(position.max_y, max_y)
                self.assertEqual(position.move(0, 100).y, max_y)

    def test_bounds_use_prepared_text_and_character_coordinates(self):
        position = LightPosition.from_text(normalize_text("\t界e\u0301\r\n"))
        # Four expanded spaces + a wide glyph + e + a combining mark = seven
        # Python characters. Converting this to terminal-cell widths is deferred.
        self.assertEqual((position.max_x, position.max_y), (6, 1))

    def test_rejects_invalid_bounds_and_initial_positions(self):
        for max_x, max_y, x, y in (
            (-1, 0, 0, 0),
            (0, -1, 0, 0),
            (2, 2, -1, 0),
            (2, 2, 0, -1),
            (2, 2, 3, 0),
            (2, 2, 0, 3),
        ):
            with self.subTest(max_x=max_x, max_y=max_y, x=x, y=y):
                with self.assertRaises(ValueError):
                    LightPosition(max_x=max_x, max_y=max_y, x=x, y=y)
