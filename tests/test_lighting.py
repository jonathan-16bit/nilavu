"""Check the light's mathematical behavior without starting the UI."""

import math
import unittest

from nilavu.lighting import LightSettings, brightness_at


class LightSettingsTests(unittest.TestCase):
    def test_defaults_preserve_existing_geometry(self):
        settings = LightSettings()
        self.assertEqual((settings.radius, settings.cell_aspect_ratio), (12.0, 2.0))

    def test_invalid_geometry_and_overflowing_row_extent_are_rejected(self):
        for value in (0.0, -1.0, math.nan, math.inf, -math.inf):
            for settings in ((value, 2.0), (12.0, value)):
                with self.subTest(settings=settings):
                    with self.assertRaises(ValueError):
                        LightSettings(*settings)
        with self.assertRaisesRegex(ValueError, "divided"):
            LightSettings(1e308, 1e-308)


class BrightnessTests(unittest.TestCase):
    def test_center_is_fully_bright_for_different_radii(self):
        for radius in (0.25, 1.0, 10.0):
            with self.subTest(radius=radius):
                self.assertEqual(brightness_at(12, 7, 12, 7, radius), 1.0)

    def test_smoothstep_values_at_known_distances(self):
        # These values distinguish the approved soft curve from a linear ramp.
        for distance, expected in ((1, 0.84375), (2, 0.5), (3, 0.15625)):
            with self.subTest(distance=distance):
                self.assertEqual(brightness_at(distance, 0, 0, 0, 4.0), expected)

    def test_brightness_decreases_and_stays_in_range(self):
        values = [brightness_at(x, 0, 0, 0, 10.0) for x in range(11)]
        self.assertTrue(all(0.0 <= value <= 1.0 for value in values))
        self.assertTrue(all(left > right for left, right in zip(values, values[1:])))
        self.assertEqual(
            values, [brightness_at(x, 0, 0, 0, 10.0) for x in range(11)]
        )

    def test_equal_radial_distances_have_equal_brightness(self):
        # A 3-4-5 triangle checks both axes together, not just horizontal distance.
        expected = brightness_at(15, 20, 10, 20, 8.0)
        for dx, dy in ((-5, 0), (0, 5), (0, -5), (3, 4), (-3, -4)):
            with self.subTest(dx=dx, dy=dy):
                self.assertEqual(
                    brightness_at(10 + dx, 20 + dy, 10, 20, 8.0), expected
                )

    def test_translating_light_and_source_does_not_change_brightness(self):
        self.assertEqual(
            brightness_at(3, 4, 0, 0, 10.0),
            brightness_at(103, 54, 100, 50, 10.0),
        )

    def test_radius_boundary_and_outside_are_completely_dark(self):
        for x, y in ((5, 0), (3, 4), (6, 0), (50, 50)):
            with self.subTest(x=x, y=y):
                self.assertEqual(brightness_at(x, y, 0, 0, 5.0), 0.0)
        self.assertEqual(brightness_at(1, 0, 0, 0, 0.25), 0.0)

    def test_rejects_nonpositive_and_nonfinite_radii(self):
        for radius in (0.0, -1.0, math.inf, -math.inf, math.nan):
            with self.subTest(radius=radius):
                with self.assertRaisesRegex(ValueError, "finite and positive"):
                    brightness_at(0, 0, 0, 0, radius)

    def test_cell_aspect_ratio_matches_equal_physical_distances(self):
        # Different positive ratios remain tunable: one row equals ratio columns.
        for ratio in (0.5, 1.0, 2.0, 3.0):
            with self.subTest(ratio=ratio):
                vertical = brightness_at(4, 7, 4, 5, 10.0, cell_aspect_ratio=ratio)
                horizontal = brightness_at(4 + int(2 * ratio), 5, 4, 5, 10.0)
                self.assertEqual(vertical, horizontal)
                self.assertEqual(
                    vertical,
                    brightness_at(4, 3, 4, 5, 10.0, cell_aspect_ratio=ratio),
                )

    def test_ratio_two_reaches_vertical_boundary_after_five_rows(self):
        self.assertEqual(brightness_at(0, 5, 0, 0, 10.0, cell_aspect_ratio=2.0), 0.0)
        self.assertGreater(brightness_at(0, 4, 0, 0, 10.0, cell_aspect_ratio=2.0), 0.0)
        self.assertEqual(brightness_at(0, 0, 0, 0, 10.0, cell_aspect_ratio=2.0), 1.0)

    def test_rejects_nonpositive_and_nonfinite_cell_ratios(self):
        for ratio in (0.0, -1.0, math.inf, -math.inf, math.nan):
            with self.subTest(ratio=ratio):
                with self.assertRaisesRegex(ValueError, "Cell aspect ratio"):
                    brightness_at(0, 0, 0, 0, 10.0, cell_aspect_ratio=ratio)
