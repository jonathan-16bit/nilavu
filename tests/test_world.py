"""Check repeatability, text volume, and reachable open woodland."""

from collections import deque
import unittest

from nilavu.cells import line_width
from nilavu.world import generate_world, Terrain


class WorldTests(unittest.TestCase):
    def test_fixed_dimensions_and_connected_ground_across_seeds(self):
        for seed in range(40):
            with self.subTest(seed=seed):
                world = generate_world("def grow_tree(): return moss", str(seed))
                self.assertEqual((world.width, world.height), (60, 24))
                self.assertTrue(world.passable(*world.spawn))
                self.assertEqual(world.terrain[world.pond[1]][world.pond[0]], Terrain.WATER)
                seen = {world.spawn}
                queue = deque(seen)
                while queue:
                    x, y = queue.popleft()
                    for cell in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)):
                        if cell not in seen and world.passable(*cell):
                            seen.add(cell)
                            queue.append(cell)
                ground = {(x,y) for y in range(world.height) for x in range(world.width)
                          if world.passable(x,y)}
                self.assertEqual(seen, ground)
                self.assertGreater(len(ground), 60 * 24 * 0.85)
                self.assertFalse(world.passable(-1, 0))
                self.assertFalse(world.passable(60, 0))

    def test_seed_repeatability_and_file_structure_does_not_determine_terrain(self):
        first = generate_world("short", "fern")
        self.assertEqual(first, generate_world("short", "fern"))
        self.assertEqual(first.terrain, generate_world("many\n" * 10000, "fern").terrain)
        self.assertEqual(first.terrain, generate_world("", "fern").terrain)
        self.assertNotEqual(first.terrain, generate_world("short", "pond").terrain)

    def test_text_reuse_sampling_and_unicode_stay_within_world_columns(self):
        for text in ("", "fern", "நிலவு 森 a\u0301", "\u0301" * 100000,
                     " ".join(f"word{n}" for n in range(10000))):
            with self.subTest(length=len(text)):
                world = generate_world(text, "fern")
                self.assertEqual(len(world.lines), 24)
                self.assertTrue(all(line_width(line) == 60 for line in world.lines))
                self.assertLess(len(world.text), 100000)
                if not text:
                    self.assertEqual(set(world.text), {" ", "\n"})
                if text == "fern":
                    self.assertGreater(world.text.count("fern"), 24)
        sampled = generate_world(" ".join(f"word{n}" for n in range(10000)), "fern").text
        self.assertTrue(any(int(word[4:]) > 5000 for word in sampled.split()))
