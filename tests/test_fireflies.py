"""Verify reachable discoveries, interaction range, and permanent collection."""

from collections import deque
import unittest

from nilavu.fireflies import Firefly, FireflyRun, at_pond_bank, new_run, sleeping_glow_frames
from nilavu.world import generate_world


class FireflyTests(unittest.TestCase):
    def test_placement_repeats_and_is_reachable_across_seeds(self):
        for seed in ["fern", "", "森", "\udcff"] + [str(i) for i in range(40)]:
            with self.subTest(seed=ascii(seed)):
                world = generate_world(seed)
                run = new_run(world, seed)
                self.assertEqual(run, new_run(world, seed))
                self.assertEqual(len(run.fireflies), 3)
                self.assertEqual(run.awake_count, 0)
                positions = {fly.position for fly in run.fireflies}
                self.assertEqual(len(positions), 3)
                self.assertNotIn(world.spawn, positions)
                reached, queue = {world.spawn}, deque([world.spawn])
                while queue:
                    x, y = queue.popleft()
                    for cell in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                        if cell not in reached and world.passable(*cell):
                            reached.add(cell)
                            queue.append(cell)
                self.assertTrue(positions <= reached)
                self.assertIn(world.pond_bank, reached)
                for x, y in positions:
                    self.assertEqual(world.lines[y][x], " ")
                for first in positions:
                    for second in positions - {first}:
                        self.assertGreater(abs(first[0] - second[0]) + abs(first[1] - second[1]), 20)

    def test_only_nearest_sleeper_wakes_and_collection_is_permanent(self):
        run = FireflyRun((Firefly((10, 10)), Firefly((12, 10)), Firefly((30, 10))))
        self.assertIs(run.wake_nearby((0, 0), 2), run)
        awake = run.wake_nearby((10, 10), 2)
        self.assertEqual(awake.awake_count, 1)
        self.assertTrue(awake.fireflies[0].awake)
        self.assertFalse(awake.fireflies[1].awake)
        # A second press can wake a different nearby sleeper, never recount one.
        awake = awake.wake_nearby((10, 10), 2)
        self.assertEqual(awake.awake_count, 2)
        self.assertIs(awake.wake_nearby((10, 10), 2), awake)
        self.assertEqual(run.awake_count, 0)
        self.assertEqual(awake.wake_nearby((30, 10), 2).awake_count, 3)

    def test_range_uses_the_configured_terminal_geometry(self):
        run = FireflyRun((Firefly((10, 10)),))
        self.assertEqual(run.nearest_sleeping((7, 10), 2), 0)
        self.assertEqual(run.nearest_sleeping((10, 9), 2), 0)
        self.assertIsNone(run.nearest_sleeping((10, 8), 2))
        self.assertEqual(run.nearest_sleeping((10, 8), 1), 0)

    def test_sleeping_glow_is_small_faint_and_pulses(self):
        world = generate_world("fern")
        position = new_run(world, "fern").fireflies[0].position
        frames = sleeping_glow_frames(world, position, 2)
        self.assertGreater(len({frame[position] for frame in frames}), 1)
        self.assertTrue(all(0 < value <= 0.5 for frame in frames for value in frame.values()))
        x, y = position
        self.assertTrue(all(abs(cx - x) <= 5 and abs(cy - y) <= 3
                            for frame in frames for cx, cy in frame))

    def test_count_and_geometry_validation(self):
        world = generate_world("fern")
        self.assertEqual(len(new_run(world, "fern", count=1).fireflies), 1)
        for count in (0, 4):
            with self.assertRaises(ValueError):
                new_run(world, "fern", count=count)
        run = new_run(world, "fern")
        for ratio in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                run.nearest_sleeping(world.spawn, ratio)
            with self.assertRaises(ValueError):
                sleeping_glow_frames(world, run.fireflies[0].position, ratio)

    def test_finale_requires_every_discovery_and_a_walkable_shore_interaction(self):
        world = generate_world("fern")
        for count in (1, 2, 3):
            run = new_run(world, "fern", count=count)
            self.assertIs(run.finish_nearby(world, world.pond_bank, 2), run)
            for fly in run.fireflies:
                run = run.wake_nearby(fly.position, 2)
            self.assertFalse(run.completed)
            self.assertIs(run.finish_nearby(world, world.spawn, 2), run)
            self.assertIs(run.finish_nearby(world, world.pond, 2), run)
            finished = run.finish_nearby(world, world.pond_bank, 2)
            self.assertTrue(finished.completed)
            self.assertEqual(finished.awake_count, count)
            self.assertIs(finished.finish_nearby(world, world.pond_bank, 2), finished)
        x, y = world.pond_bank
        self.assertTrue(at_pond_bank(world, (x - 3, y), 2))
        self.assertFalse(at_pond_bank(world, (x - 4, y), 2))
        self.assertTrue(at_pond_bank(world, (x, y - 1), 2))
        self.assertFalse(at_pond_bank(world, (x, y - 2), 2))
        self.assertTrue(at_pond_bank(world, (x, y - 2), 1))
        for ratio in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                at_pond_bank(world, world.pond_bank, ratio)
