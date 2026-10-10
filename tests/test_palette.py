"""Check coherent shade and cursor roles for every selectable preset."""

import unittest

from rich.style import Style

from nilavu.palette import PALETTES, SHADE_LEVELS


class PaletteTests(unittest.TestCase):
    def test_presets_have_five_distinct_shades_with_shared_darkness(self):
        for name, palette in PALETTES.items():
            with self.subTest(theme=name):
                shades = [Style.parse(palette.style_at(level / (SHADE_LEVELS - 1)))
                          for level in range(SHADE_LEVELS)]
                self.assertEqual(len(set(shades)), SHADE_LEVELS)
                self.assertEqual(shades[0].color.triplet, palette.background)
                self.assertEqual(shades[0].bgcolor.triplet, palette.background)
                self.assertEqual(shades[-1].color.triplet, palette.foreground)
                self.assertEqual(shades[-1].bgcolor.triplet, palette.cell_background)
                cursor = Style.parse(palette.cursor_style())
                self.assertEqual(cursor.color.triplet, palette.background)
                self.assertNotIn(cursor.bgcolor, [shade.bgcolor for shade in shades])
