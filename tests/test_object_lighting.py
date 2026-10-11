"""Check local object illumination without involving terminal rendering."""

import unittest

from nilavu.object_lighting import glow_field
from nilavu.world import generate_world, Terrain


class ObjectLightingTests(unittest.TestCase):
    def test_glows_are_local_quantized_and_use_terminal_geometry(self):
        world = generate_world("fern")
        field = glow_field(world, 2.0)
        lx, ly = next(mark.position for mark in world.landmarks
                      if mark.name == "lantern clearing")
        self.assertEqual(field[ly][lx].brightness, 1)
        self.assertEqual(field[ly][lx].color, (255, 183, 75))
        self.assertEqual(field[ly][lx + 4], field[ly + 2][lx])
        self.assertEqual(field[0][0].brightness, 0)
        self.assertTrue(all(glow.level in range(5) for row in field for glow in row))
        for y, row in enumerate(world.terrain):
            for x, kind in enumerate(row):
                if kind == Terrain.CRYSTAL:
                    self.assertGreater(field[y][x].brightness, 0)
                    self.assertEqual(field[y][x].color, (173, 133, 255))
        self.assertEqual(field, glow_field(world, 2.0))

    def test_invalid_cell_geometry_is_rejected(self):
        world = generate_world("fern")
        for ratio in (0, -1, float("nan"), float("inf")):
            with self.subTest(ratio=ratio), self.assertRaises(ValueError):
                glow_field(world, ratio)
