"""Check theme selection, repeatable generation, and readable color roles."""

import unittest

from rich.style import Style

from nilavu.palette import DEFAULT_PALETTE, DEFAULT_THEME, THEMES, next_seed, palette_for, SHADE_LEVELS


class PaletteTests(unittest.TestCase):
    def test_presets_have_five_distinct_shades_with_shared_darkness(self):
        for name in THEMES:
            palette = palette_for(name)
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

    def test_only_two_themes_and_moonlight_is_the_default(self):
        self.assertEqual(THEMES, ("moonlight", "forest"))
        self.assertEqual(DEFAULT_THEME, "moonlight")
        self.assertIs(palette_for(DEFAULT_THEME), DEFAULT_PALETTE)
        self.assertIs(palette_for("moonlight", "fern"), DEFAULT_PALETTE)
        for name in ("green", "ember", "unknown"):
            with self.assertRaises(ValueError):
                palette_for(name)

    def test_forest_seed_is_repeatable_and_varies_colors(self):
        self.assertEqual(palette_for("forest", "fern"), palette_for("forest", "fern"))
        palettes = {palette_for("forest", str(seed)) for seed in range(100)}
        self.assertEqual(len(palettes), 100)
        # Fixed example catches accidental changes to reproducible seed mapping.
        self.assertEqual(palette_for("forest", "moss").background, (12, 19, 11))
        self.assertEqual(palette_for("forest", ""), palette_for("forest", ""))
        palette_for("forest", "\udcff")

    def test_generated_palettes_keep_lit_text_and_cursor_readable(self):
        def luminance(rgb):
            channels = [channel / 255 for channel in rgb]
            linear = [value / 12.92 if value <= 0.04045 else
                      ((value + 0.055) / 1.055) ** 2.4 for value in channels]
            return sum(value * weight for value, weight in
                       zip(linear, (0.2126, 0.7152, 0.0722)))

        def contrast(first, second):
            bright, dark = sorted((luminance(first), luminance(second)), reverse=True)
            return (bright + 0.05) / (dark + 0.05)

        for seed in range(256):
            palette = palette_for("forest", str(seed))
            with self.subTest(seed=seed):
                self.assertGreaterEqual(contrast(palette.foreground, palette.cell_background), 4.5)
                self.assertGreaterEqual(contrast(palette.cursor_background, palette.background), 4.5)
                self.assertEqual(len({palette.style_at(level / 4) for level in range(5)}), 5)

    def test_seed_sequence_is_repeatable_and_can_resume_from_a_displayed_seed(self):
        seed = "fern"
        sequence = []
        for _ in range(20):
            seed = next_seed(seed)
            self.assertRegex(seed, r"^[0-9a-f]{8}$")
            sequence.append(seed)
        self.assertEqual(len(set(sequence)), 20)
        self.assertEqual(next_seed("fern"), sequence[0])
        self.assertEqual(next_seed(sequence[0]), sequence[1])
        self.assertNotEqual(next_seed("moss"), sequence[0])
        self.assertEqual(next_seed("\udcff"), next_seed("\udcff"))
