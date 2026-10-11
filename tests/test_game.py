"""Exercise collisions, fixed map boundaries, resizing, and game seeds."""

import unittest
from textual.geometry import Region

from nilavu.game import ForestApp
from nilavu.navigation import LightPosition
from nilavu.palette import next_seed
from nilavu.world_view import WorldView
from nilavu.world import Terrain


class GameTests(unittest.IsolatedAsyncioTestCase):
    async def test_world_stays_fixed_when_zooming_out_and_in(self):
        app = ForestApp(seed="pond", reveal=True)
        async with app.run_test(size=(200, 60)) as pilot:
            world = app.world
            source = app.query_one(WorldView)
            self.assertEqual(source.size.width, 180)
            self.assertEqual(source.size.height, 48)
            self.assertEqual(source.region, Region(9, 5, 182, 50))
            self.assertEqual(len(source.render_line(0).text), 180)
            self.assertTrue(app.screen.styles.background.ansi == -1)
            await pilot.resize_terminal(30, 12)
            self.assertIs(app.world, world)
            self.assertEqual((source.size.width, source.size.height), (28, 10))
            self.assertGreater(source.viewport.y, 0)
            await pilot.resize_terminal(210, 70)
            self.assertIs(app.world, world)
            self.assertEqual((source.size.width, source.size.height), (180, 48))
            self.assertEqual((source.viewport.x, source.viewport.y), (0, 0))
            await pilot.resize_terminal(1, 1)
            await pilot.press("q")
            self.assertFalse(app.is_running)

    async def test_blocked_terrain_and_seed_restart(self):
        app = ForestApp(seed="fern")
        async with app.run_test(size=(80, 30)) as pilot:
            source = app.query_one(WorldView)
            # Find accessible ground beside water and try to step into it.
            for y in range(app.world.height):
                for x in range(app.world.width - 1):
                    if app.world.passable(x,y) and not app.world.passable(x+1,y):
                        start = (x,y)
                        break
                else:
                    continue
                break
            app.light_position = LightPosition(app.world.width - 1, app.world.height - 1, *start)
            source.update_light(app.light_position)
            await pilot.press("right")
            self.assertEqual((app.light_position.x, app.light_position.y), start)
            previous = app.world
            await pilot.press("t")
            self.assertIs(app.world, previous)
            await pilot.press("r")
            self.assertEqual(app.seed, next_seed("fern"))
            self.assertIsNot(app.world, previous)
            self.assertIs(source.world, app.world)
            self.assertEqual((app.light_position.x, app.light_position.y), app.world.spawn)
            self.assertIn(app.seed, str(source.border_subtitle))
            self.assertFalse(source.reveal)
            await pilot.press("q")

    async def test_reveal_changes_illumination_without_changing_terrain(self):
        app = ForestApp(seed="moss")
        async with app.run_test(size=(200, 60)) as pilot:
            source = app.query_one(WorldView)
            x, y = app.world.pond
            before = list(source.render_line(y))[x].style.bgcolor.triplet
            self.assertEqual(before, app.palette.background)
            self.assertEqual(list(source.render_line(y))[x].style.color.triplet,
                             app.palette.background)
            terrain = app.world.terrain
            source.reveal = True
            source.refresh()
            await pilot.pause()
            after = list(source.render_line(y))[x].style.bgcolor.triplet
            self.assertNotEqual(after, before)
            self.assertNotEqual(list(source.render_line(y))[x].style.color.triplet,
                                app.palette.background)
            self.assertIs(app.world.terrain, terrain)
            self.assertFalse(app.world.passable(x,y))

    async def test_terrain_has_distinct_foregrounds_and_cursor_priority(self):
        app = ForestApp(seed="fern", reveal=True)
        async with app.run_test(size=(200, 60)) as pilot:
            source = app.query_one(WorldView)
            colors = {}
            for y in range(app.world.height):
                for x, segment in enumerate(source.render_line(y)):
                    if (x, y) == app.world.spawn:
                        self.assertEqual(segment.style.bgcolor.triplet,
                                         app.palette.cursor_background)
                    else:
                        colors[app.world.terrain[y][x]] = segment.style.color.triplet
            self.assertEqual(set(colors), set(Terrain))
            self.assertEqual(len(set(colors.values())), len(Terrain))
            await pilot.press("t")
            x, y = app.world.pond
            self.assertNotEqual(list(source.render_line(y))[x].style.color.triplet,
                                colors[Terrain.WATER])
