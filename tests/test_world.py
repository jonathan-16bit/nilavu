"""Check repeatability, text volume, and reachable open woodland."""

from collections import deque
import unittest

from nilavu.cells import line_width, visible_cells
from nilavu.world import generate_world, Terrain


class WorldTests(unittest.TestCase):
    def test_fixed_dimensions_and_connected_ground_across_seeds(self):
        for seed in range(40):
            with self.subTest(seed=seed):
                world = generate_world("def grow_tree(): return moss", str(seed))
                self.assertEqual((world.width, world.height), (140, 32))
                self.assertTrue(world.passable(*world.spawn))
                # Groves must occupy the added area, not just the old map bounds.
                self.assertTrue(any(cell == Terrain.CANOPY
                                    for row in world.terrain[24:] for cell in row[60:]))
                canopy = sum(cell == Terrain.CANOPY for row in world.terrain for cell in row)
                self.assertLess(canopy, world.width * world.height * 0.30)
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
                self.assertGreater(len(ground), 140 * 32 * 0.85)
                self.assertFalse(world.passable(-1, 0))
                self.assertFalse(world.passable(140, 0))

    def test_seed_repeatability_and_file_structure_does_not_determine_terrain(self):
        first = generate_world("short", "fern")
        self.assertEqual(first, generate_world("short", "fern"))
        self.assertEqual(first.terrain, generate_world("many\n" * 10000, "fern").terrain)
        self.assertEqual(first.terrain, generate_world("", "fern").terrain)
        self.assertNotEqual(first.terrain, generate_world("short", "pond").terrain)

    def test_text_reuse_sampling_and_unicode_stay_within_world_columns(self):
        for text in ("", "fern", "நிலவு 森 a\u0301", "森", "a" + "\u0301" * 100000, "\u0301" * 100000,
                     " ".join(f"word{n}" for n in range(10000))):
            with self.subTest(length=len(text)):
                world = generate_world(text, "fern")
                self.assertEqual(len(world.lines), 32)
                self.assertTrue(all(line_width(line) == 140 for line in world.lines))
                self.assertLess(len(world.text), 100000)
                if not text:
                    self.assertEqual(set(world.text), {" ", "\n"})
                if text == "fern":
                    self.assertGreater(sum(world.text.count(c) for c in "fern"), 40)
                    self.assertLessEqual(set(world.text), set("fern \n"))
        sampled = generate_world("aaaa " * 5000 + "ZZZZ " * 5000, "fern").text
        self.assertIn("Z", sampled)
        self.assertIn("a", sampled)

    def test_scenery_density_and_wide_glyphs_follow_terrain(self):
        world = generate_world("Q", "fern")
        counts = {kind: [0, 0] for kind in Terrain}
        for y, row in enumerate(world.terrain):
            for x, kind in enumerate(row):
                counts[kind][0] += 1
                counts[kind][1] += world.lines[y][x] != " "
        for kind in Terrain:
            self.assertGreater(counts[kind][0], 0)
        self.assertGreater(counts[Terrain.CANOPY][1] / counts[Terrain.CANOPY][0], 0.60)
        for kind in (Terrain.MOSS, Terrain.GRASS, Terrain.EARTH):
            self.assertEqual(counts[kind][1], 0)
        self.assertEqual(counts[Terrain.TRUNK][0], counts[Terrain.TRUNK][1])
        self.assertEqual(counts[Terrain.FLOWER][0], counts[Terrain.FLOWER][1])
        self.assertTrue(all(world.passable(x, y) for y, row in enumerate(world.terrain)
                            for x, kind in enumerate(row) if kind == Terrain.FLOWER))
        for y, row in enumerate(world.terrain):
            for x, kind in enumerate(row):
                if kind == Terrain.WATER and y % 2:
                    self.assertEqual(world.lines[y][x], " ")
        wide = generate_world("森", "fern")
        self.assertIn("森", wide.text)
        for y, line in enumerate(wide.lines):
            for x, glyph, cells in visible_cells(line, 0, wide.width):
                if cells == 2:
                    self.assertEqual(wide.terrain[y][x], wide.terrain[y][x + 1])
