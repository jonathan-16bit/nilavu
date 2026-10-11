"""Check local object illumination without involving terminal rendering."""

import unittest

from nilavu.object_lighting import ANIMATION_FRAMES, glow_field, water_highlight
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

    def test_animation_is_bounded_repeatable_and_stays_local(self):
        world = generate_world("fern")
        frames = [glow_field(world, 2.0, frame=i) for i in range(ANIMATION_FRAMES)]
        self.assertEqual(frames[0], glow_field(world, 2.0, frame=ANIMATION_FRAMES))
        self.assertNotEqual(frames[0], frames[1])
        lx, ly = next(mark.position for mark in world.landmarks
                      if mark.name == "lantern clearing")
        self.assertEqual({frame[ly][lx].level for frame in frames}, {3, 4})
        for y, row in enumerate(world.terrain):
            for x, kind in enumerate(row):
                levels = {frame[y][x].level for frame in frames}
                self.assertLessEqual(max(levels) - min(levels), 1)
                if kind == Terrain.CRYSTAL:
                    self.assertTrue(levels <= {2, 3})
        self.assertTrue(all(frame[0][0].level == 0 for frame in frames))

    def test_water_highlights_are_sparse_and_move_in_a_closed_loop(self):
        for y in range(4):
            for frame in range(ANIMATION_FRAMES):
                self.assertEqual(sum(water_highlight(x, y, frame)
                                     for x in range(ANIMATION_FRAMES)), 2)
                self.assertEqual(water_highlight(5, y, frame),
                                 water_highlight(5, y, frame + ANIMATION_FRAMES))
        self.assertNotEqual([water_highlight(x, 0, 0) for x in range(12)],
                            [water_highlight(x, 0, 1) for x in range(12)])
