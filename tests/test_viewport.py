"""Check edge-following and resize behavior independently of the UI."""

import unittest

from nilavu.navigation import LightPosition
from nilavu.viewport import Viewport


class ViewportTests(unittest.TestCase):
    def test_radius_margins_trigger_before_each_screen_edge(self):
        view = Viewport(20, 20)
        # A 40 x 20 screen leaves an interior of x=12..27 and y=6..13.
        for position, expected in (
            ((32, 26), view),
            ((47, 33), view),
            ((48, 30), Viewport(21, 20)),
            ((31, 30), Viewport(19, 20)),
            ((40, 34), Viewport(20, 21)),
            ((40, 25), Viewport(20, 19)),
        ):
            with self.subTest(position=position):
                self.assertEqual(
                    view.follow(LightPosition(99, 99, *position), 40, 20,
                                margin_x=12, margin_y=6), expected,
                )

    def test_small_screens_cap_margins_and_follow_is_stable(self):
        light = LightPosition(99, 99, 40, 40)
        for width, height, expected in (
            (5, 3, Viewport(38, 39)),
            (4, 2, Viewport(38, 39)),
            (1, 1, Viewport(40, 40)),
        ):
            with self.subTest(size=(width, height)):
                view = Viewport().follow(light, width, height, margin_x=12, margin_y=6)
                self.assertEqual(view, expected)
                self.assertEqual(
                    view.follow(light, width, height, margin_x=12, margin_y=6), view
                )

    def test_document_boundaries_override_radius_margins(self):
        for position, expected in (((0, 0), Viewport()), ((49, 29), Viewport(10, 10))):
            with self.subTest(position=position):
                self.assertEqual(
                    Viewport(5, 5).follow(LightPosition(49, 29, *position), 40, 20,
                                          margin_x=12, margin_y=6), expected,
                )

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
