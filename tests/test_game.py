"""Exercise collisions, fixed map boundaries, resizing, and game seeds."""

import unittest
from textual.geometry import Region

from nilavu.game import ForestApp
from nilavu.navigation import LightPosition
from nilavu.object_lighting import ANIMATION_FRAMES
from nilavu.palette import next_seed
from nilavu.world_view import WorldView
from nilavu.world import Terrain


class GameTests(unittest.IsolatedAsyncioTestCase):
    async def test_animation_updates_styles_without_changing_world_or_cursor(self):
        app = ForestApp(seed="fern", reveal=True)
        async with app.run_test(size=(200, 60)) as pilot:
            source = app.query_one(WorldView)
            # Freeze real time so every cached frame is checked deterministically.
            source._animation_timer.pause()
            source._animation_frame = 0
            world, position = app.world, app.light_position
            expected_rows = [list(row) for row in world.lines]
            for fly in app.firefly_run.fireflies:
                x, y = fly.position
                expected_rows[y][x] = "i"
            expected_text = "\n".join("".join(row) for row in expected_rows)
            frames = []
            for _ in range(ANIMATION_FRAMES):
                content = source.render()
                frames.append(tuple(span.style for span in content.spans))
                x, y = world.spawn
                self.assertEqual(content.spans[y * world.width + x].style,
                                 app.palette.cursor_style())
                self.assertEqual(content.plain, expected_text)
                source._advance_animation()
            self.assertGreater(len(set(frames)), 1)
            for kind in (Terrain.WATER, Terrain.CRYSTAL, Terrain.LANTERN):
                indexes = [y * world.width + x for y, row in enumerate(world.terrain)
                           for x, terrain in enumerate(row) if terrain == kind]
                self.assertGreater(len({tuple(frame[i] for i in indexes)
                                        for frame in frames}), 1)
            self.assertEqual(source._animation_frame, 0)
            self.assertIs(app.world, world)
            self.assertEqual(app.light_position, position)
            await pilot.press("t")
            await pilot.press("r")
            self.assertEqual(source._animation_frame, 0)
            self.assertEqual(len(source._glow_frames), ANIMATION_FRAMES)
            timer = source._animation_timer
            await pilot.press("q")
        self.assertIsNone(timer._task)

    async def test_waking_progress_theme_resize_and_seed_reset(self):
        app = ForestApp(seed="fern")
        async with app.run_test(size=(80, 30)) as pilot:
            source = app.query_one(WorldView)
            await pilot.press("space")
            self.assertEqual(app.firefly_run.awake_count, 0)
            original = app.firefly_run
            for i, fly in enumerate(original.fireflies):
                app.light_position = LightPosition(app.world.width - 1, app.world.height - 1,
                                                   *fly.position)
                source.update_light(app.light_position)
                # Exercise the ordinary input path to update the contextual help.
                app.action_move_light(0, 0)
                self.assertIn("Space: wake", str(source.border_title))
                await pilot.press("space", "space")
                self.assertEqual(app.firefly_run.awake_count, i + 1)
                self.assertEqual(source.fireflies, app.firefly_run.fireflies)
            self.assertIn("all awake", str(source.border_title))
            run = app.firefly_run
            await pilot.press("t")
            await pilot.resize_terminal(35, 14)
            self.assertIs(app.firefly_run, run)
            await pilot.press("r")
            self.assertEqual(app.firefly_run.awake_count, 0)
            self.assertNotEqual(app.firefly_run, run)
            self.assertEqual(source.fireflies, app.firefly_run.fireflies)
            self.assertIn("0/3 awake", str(source.border_title))

    async def test_sleepers_appear_only_nearby_and_cursor_keeps_priority(self):
        app = ForestApp(seed="fern")
        async with app.run_test(size=(200, 60)) as pilot:
            source = app.query_one(WorldView)
            source._animation_timer.pause()
            fly = app.firefly_run.fireflies[0]
            x, y = fly.position
            # The underlying terrain is blank, and remains unmodified by markers.
            self.assertEqual(app.world.lines[y][x], " ")
            self.assertEqual(source.render().plain.splitlines()[y][x], " ")
            app.light_position = LightPosition(app.world.width - 1, app.world.height - 1, x - 18, y)
            source.update_light(app.light_position)
            content = source.render()
            self.assertEqual(content.plain.splitlines()[y][x], "i")
            self.assertNotEqual(content.spans[y * app.world.width + x].style,
                                app.palette.style_at(0))
            app.light_position = LightPosition(app.world.width - 1, app.world.height - 1, x, y)
            source.update_light(app.light_position)
            self.assertEqual(source.render().spans[y * app.world.width + x].style,
                             app.palette.cursor_style())
            await pilot.press("space")
            self.assertEqual(source.render().plain.splitlines()[y][x], " ")
            self.assertEqual(app.world.lines[y][x], " ")

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

    async def test_object_glow_survives_cursor_distance_and_refreshes_with_seed(self):
        app = ForestApp(seed="fern")
        async with app.run_test(size=(200, 60)) as pilot:
            source = app.query_one(WorldView)
            def lantern_color():
                x, y = next(mark.position for mark in app.world.landmarks
                            if mark.name == "lantern clearing")
                return list(source.render_line(y))[x].style.bgcolor.triplet
            self.assertNotEqual(lantern_color(), app.palette.background)
            terrain, lines = app.world.terrain, app.world.lines
            await pilot.press("t")
            self.assertNotEqual(lantern_color(), app.palette.background)
            self.assertEqual(app.world.terrain, terrain)
            self.assertEqual(app.world.lines, lines)
            await pilot.press("r")
            self.assertNotEqual(lantern_color(), app.palette.background)
