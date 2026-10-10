"""Check edge-following and resize behavior independently of the UI."""

import unittest

from nilavu.navigation import LightPosition
from nilavu.viewport import Viewport


class ViewportTests(unittest.TestCase):
    def test_visible_light_does_not_scroll(self):
        view = Viewport(3, 4)
        self.assertEqual(view.follow(LightPosition(29, 29, 7, 6), 8, 5), view)

    def test_crossing_each_edge_scrolls_just_enough(self):
        for position, expected in (
            ((11, 6), Viewport(4, 4)),
            ((2, 6), Viewport(2, 4)),
            ((7, 9), Viewport(3, 5)),
            ((7, 3), Viewport(3, 3)),
        ):
            with self.subTest(position=position):
                self.assertEqual(
                    Viewport(3, 4).follow(LightPosition(29, 29, *position), 8, 5),
                    expected,
                )

    def test_shrink_keeps_light_visible_and_growth_removes_overscroll(self):
        light = LightPosition(19, 9, 19, 9)
        view = Viewport().follow(light, 8, 4)
        self.assertEqual(view, Viewport(12, 6))
        self.assertEqual(view.follow(light, 5, 2), Viewport(15, 8))
        self.assertEqual(view.follow(light, 30, 20), Viewport())

    def test_short_and_empty_documents_stay_at_origin(self):
        for text in ("", "abc\nx\n"):
            light = LightPosition.from_text(text)
            self.assertEqual(Viewport(4, 5).follow(light, 8, 4), Viewport())

    def test_zero_area_waits_for_layout(self):
        view = Viewport(3, 4)
        for width, height in ((0, 4), (8, 0)):
            self.assertEqual(view.follow(LightPosition(29, 29), width, height), view)
