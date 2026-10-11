"""Check bounded following, idle gathering, and decorative companion light."""

from dataclasses import replace
import math
import unittest

from nilavu.companions import Companions, companion_glow
from nilavu.world import Terrain, World


def clearing() -> World:
    return World(tuple((Terrain.MOSS,) * 30 for _ in range(12)),
                 (" " * 30,) * 12, (3, 5), (25, 8), ())


class CompanionTests(unittest.TestCase):
    def test_follows_recent_steps_in_order_with_bounded_history(self):
        world = clearing()
        group = Companions((world.spawn,))
        for _ in range(3):
            group = group.add(world.spawn)
        for x in range(4, 20):
            group = group.follow(world, (x, 5), 2)
        self.assertEqual(group.positions, ((17, 5), (15, 5), (13, 5)))
        self.assertLessEqual(len(group.trail), 7)
        group = group.follow(world, (19, 4), 2)
        self.assertEqual(group.positions[0], (18, 5))
        self.assertEqual(len(set(group.positions)), 3)

    def test_fast_movement_and_edges_cannot_strand_companions(self):
        world = clearing()
        group = Companions((world.spawn,)).add(world.spawn).add(world.spawn).add(world.spawn)
        for cursor in ((29, 0), (0, 11), (0, 0), (29, 11)):
            group = group.follow(world, cursor, 2)
            self.assertEqual(len(group.positions), 3)
            for x, y in group.positions:
                self.assertTrue(world.passable(x, y))
                self.assertLessEqual(math.hypot(x - cursor[0], 2 * (y - cursor[1])), 12)

    def test_idle_gathering_avoids_symbols_and_preserves_terrain(self):
        world = clearing()
        rows = list(world.lines)
        rows[4] = rows[4][:8] + "|" + rows[4][9:]
        world = replace(world, lines=tuple(rows))
        group = Companions(((10, 5), (9, 5), (8, 5)), ((6, 5), (4, 5), (2, 5)))
        first = group.idle(world, 2)
        self.assertEqual(first.positions, group.positions)
        settled = first.idle(world, 2)
        self.assertNotEqual(settled.positions, group.positions)
        self.assertEqual(len(set(settled.positions)), 3)
        self.assertNotIn((10, 5), settled.positions)
        for x, y in settled.positions:
            self.assertEqual(world.lines[y][x], " ")
        self.assertEqual(world.lines[4][8], "|")
        self.assertEqual(settled.idle(world, 2), settled)

    def test_steady_glows_are_local_and_do_not_add_overlapping_brightness(self):
        world = clearing()
        light = companion_glow(world, ((10, 5),), 2)
        self.assertEqual(light[10, 5], 0.75)
        self.assertNotIn((0, 0), light)
        self.assertEqual(light, companion_glow(world, ((10, 5), (10, 5)), 2))
        self.assertEqual(companion_glow(world, (), 2), {})
