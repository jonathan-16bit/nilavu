"""Check repeatability, text volume, and reachable open woodland."""

from collections import deque
import unittest

from nilavu.cells import line_width, visible_cells
from nilavu.world import generate_world, Terrain


class WorldTests(unittest.TestCase):
    def test_fixed_dimensions_and_connected_ground_across_seeds(self):
        for seed in range(40):
            with self.subTest(seed=seed):
                world = generate_world(str(seed))
                self.assertEqual((world.width, world.height), (180, 48))
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
                self.assertEqual({mark.name for mark in world.landmarks},
                                 {"meadow", "rock garden", "ruined arch", "lantern clearing",
                                  "bridge", "stepping stones", "pond bank"})
                for mark in world.landmarks:
                    self.assertIn(mark.position, seen)
                kinds = {kind for row in world.terrain for kind in row}
                self.assertTrue({Terrain.ROCK, Terrain.CRYSTAL, Terrain.RUIN,
                                 Terrain.LANTERN, Terrain.BRIDGE, Terrain.STEPPING_STONE,
                                 Terrain.TRUNK, Terrain.TALL_GRASS}.issubset(kinds))
                for mark in world.landmarks:
                    if mark.name in ("bridge", "stepping stones"):
                        x, y = mark.position
                        self.assertTrue(all(world.passable(cx, y)
                                            for cx in range(x - 3, x + 5)))
                self.assertGreater(len(ground), 180 * 48 * 0.85)
                self.assertFalse(world.passable(-1, 0))
                self.assertFalse(world.passable(180, 0))

    def test_seed_reproduces_terrain_and_scenery(self):
        first = generate_world("fern")
        self.assertEqual(first, generate_world("fern"))
        second = generate_world("pond")
        self.assertNotEqual(first.terrain, second.terrain)
        self.assertNotEqual(first.lines, second.lines)

    def test_curated_symbols_fit_exact_terminal_columns(self):
        for seed in ("", "fern", "நிலவு", "森", "a" * 10000, "\udcff"):
            with self.subTest(seed=ascii(seed[:20])):
                world = generate_world(seed)
                self.assertEqual(len(world.lines), 48)
                self.assertTrue(all(line_width(line) == 180 for line in world.lines))
                self.assertTrue(all(cells == 1 for line in world.lines
                                    for _, _, cells in visible_cells(line, 0, 180)))
                self.assertNotIn("\x1b", world.text)
                self.assertLess(len(world.text), 10000)

    def test_scenery_details_follow_terrain(self):
        world = generate_world("fern")
        counts = {kind: [0, 0] for kind in Terrain}
        for y, row in enumerate(world.terrain):
            for x, kind in enumerate(row):
                counts[kind][0] += 1
                counts[kind][1] += world.lines[y][x] != " "
        for kind in Terrain:
            self.assertGreater(counts[kind][0], 0)
        self.assertGreater(counts[Terrain.CANOPY][1] / counts[Terrain.CANOPY][0], 0.60)
        for kind in (Terrain.MOSS, Terrain.GRASS, Terrain.EARTH, Terrain.MEADOW, Terrain.STONE):
            self.assertEqual(counts[kind][1], 0)
        self.assertEqual(counts[Terrain.TRUNK][0], counts[Terrain.TRUNK][1])
        self.assertEqual(counts[Terrain.FLOWER][0], counts[Terrain.FLOWER][1])
        self.assertTrue(all(world.passable(x, y) for y, row in enumerate(world.terrain)
                            for x, kind in enumerate(row) if kind == Terrain.FLOWER))
        for y, row in enumerate(world.terrain):
            for x, kind in enumerate(row):
                if kind == Terrain.WATER and y % 2:
                    self.assertEqual(world.lines[y][x], " ")
