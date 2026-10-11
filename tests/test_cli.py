"""Check CLI behavior without taking over the test runner's terminal."""

import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from nilavu.cli import main
from nilavu.lighting import LightSettings
from nilavu.palette import DEFAULT_SEED, DEFAULT_THEME, THEMES


class CliTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "source with spaces.py"
        self.path.write_bytes(b"\t[bold]\r\n\x1b[31m")
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        self.stdin = Mock()
        self.stdin.isatty.return_value = True

        # Capture messages and simulate a terminal. Replace the app only at the
        # UI boundary; CLI tests still use the real file loader and parser.
        patches = (
            patch("nilavu.cli.sys.stdin", self.stdin),
            patch("nilavu.cli.sys.stdout", self.stdout),
            patch("nilavu.cli.sys.stderr", self.stderr),
            patch.object(self.stdout, "isatty", return_value=True),
        )
        for replacement in patches:
            self.enterContext(replacement)
        self.app_factory = self.enterContext(patch("nilavu.cli.NilavuApp"))
        self.app_factory.return_value.return_code = 0
        self.game_factory = self.enterContext(patch("nilavu.cli.ForestApp"))
        self.game_factory.return_value.return_code = 0

    def test_loads_and_prepares_the_supplied_path_before_launch(self):
        self.assertEqual(main([str(self.path)]), 0)
        self.app_factory.assert_called_once_with(
            "    [bold]\n\\x1b[31m", light_settings=LightSettings(12.0, 2.0),
            theme=DEFAULT_THEME, seed=DEFAULT_SEED,
        )
        self.app_factory.return_value.run.assert_called_once_with()
        self.assertEqual(self.stdout.getvalue(), "")
        self.assertEqual(self.stderr.getvalue(), "")

    def test_loading_errors_do_not_start_the_tui(self):
        for path, message in (
            (str(Path(self.directory.name) / "missing.py"), "does not exist"),
            (self.directory.name, "regular file"),
        ):
            with self.subTest(path=path):
                self.stderr.seek(0)
                self.stderr.truncate()
                self.assertEqual(main([path]), 1)
                self.assertIn(message, self.stderr.getvalue())
        self.app_factory.assert_not_called()
        self.assertEqual(self.stdout.getvalue(), "")

    def test_geometry_options_reach_the_app(self):
        self.assertEqual(main([
            "--radius", "14.5", str(self.path), "--cell-aspect-ratio", "1.8"
        ]), 0)
        self.app_factory.assert_called_once_with(
            "    [bold]\n\\x1b[31m", light_settings=LightSettings(14.5, 1.8),
            theme=DEFAULT_THEME, seed=DEFAULT_SEED,
        )

    def test_each_theme_reaches_the_app_with_custom_geometry(self):
        for name in THEMES:
            with self.subTest(theme=name):
                self.app_factory.reset_mock()
                self.assertEqual(main([
                    str(self.path), "--theme", name, "--radius", "14"
                ]), 0)
                self.app_factory.assert_called_once_with(
                    "    [bold]\n\\x1b[31m", light_settings=LightSettings(14.0, 2.0),
                    theme=name, seed=DEFAULT_SEED,
                )

    def test_unknown_and_removed_themes_are_rejected_before_loading_or_launch(self):
        with patch("nilavu.cli.load_document") as loader:
            for theme in ("unknown", "green", "ember"):
                with self.subTest(theme=theme):
                    with self.assertRaises(SystemExit) as exit_status:
                        main([str(self.path), "--theme", theme])
                    self.assertEqual(exit_status.exception.code, 2)
            loader.assert_not_called()
        self.app_factory.assert_not_called()
        self.assertIn("invalid choice", self.stderr.getvalue())

    def test_custom_seed_and_theme_reach_the_app(self):
        for theme in THEMES:
            with self.subTest(theme=theme):
                self.app_factory.reset_mock()
                self.assertEqual(main([str(self.path), "--theme", theme, "--seed", "fern"]), 0)
                self.assertEqual(self.app_factory.call_args.kwargs["theme"], theme)
                self.assertEqual(self.app_factory.call_args.kwargs["seed"], "fern")

    def test_invalid_geometry_fails_before_loading_or_launch(self):
        with patch("nilavu.cli.load_document") as loader:
            for option in ("--radius", "--cell-aspect-ratio"):
                for value in ("0", "-1", "nan", "inf", "-inf", "nope"):
                    with self.subTest(option=option, value=value):
                        with self.assertRaises(SystemExit) as exit_status:
                            main([str(self.path), f"{option}={value}"])
                        self.assertEqual(exit_status.exception.code, 2)
            with self.assertRaises(SystemExit) as exit_status:
                main([str(self.path), "--radius=1e308", "--cell-aspect-ratio=1e-308"])
            self.assertEqual(exit_status.exception.code, 2)
            loader.assert_not_called()
        self.app_factory.assert_not_called()

    def test_rejects_redirected_input_or_output(self):
        for input_tty, output_tty in ((False, True), (True, False)):
            with self.subTest(input_tty=input_tty, output_tty=output_tty):
                self.stdin.isatty.return_value = input_tty
                with patch.object(self.stdout, "isatty", return_value=output_tty):
                    self.assertEqual(main([str(self.path)]), 1)
        self.assertIn("interactive terminal is required", self.stderr.getvalue())
        self.app_factory.assert_not_called()
        self.assertEqual(self.stdout.getvalue(), "")

    def test_help_works_without_a_terminal_or_file(self):
        self.stdin.isatty.return_value = False
        with self.assertRaises(SystemExit) as exit_status:
            main(["--help"])
        self.assertEqual(exit_status.exception.code, 0)
        self.assertIn("usage: nilavu", self.stdout.getvalue())
        self.assertIn("Press q to quit", self.stdout.getvalue())
        self.assertIn("--radius", self.stdout.getvalue())
        self.assertIn("--cell-aspect-ratio", self.stdout.getvalue())
        self.assertIn("--theme", self.stdout.getvalue())
        self.assertIn("--seed", self.stdout.getvalue())
        self.assertEqual(self.stderr.getvalue(), "")
        self.app_factory.assert_not_called()

    def test_requires_exactly_one_file_path(self):
        for arguments in ([], [str(self.path), "another.py"]):
            with self.subTest(arguments=arguments):
                with self.assertRaises(SystemExit) as exit_status:
                    main(arguments)
                self.assertEqual(exit_status.exception.code, 2)
        self.assertIn("usage: nilavu", self.stderr.getvalue())
        self.app_factory.assert_not_called()

    def test_argument_errors_neutralize_terminal_controls(self):
        with self.assertRaises(SystemExit) as exit_status:
            main([str(self.path), "\x1b]52;c;payload\x07"])
        self.assertEqual(exit_status.exception.code, 2)
        self.assertIn(r"\x1b]52;c;payload\x07", self.stderr.getvalue())
        self.assertNotIn("\x1b", self.stderr.getvalue())
        self.app_factory.assert_not_called()

    def test_double_dash_allows_a_filename_starting_with_a_dash(self):
        # Isolate this parser-only case from file lookup so we can pass a relative
        # filename beginning with a dash without changing the process directory.
        with patch("nilavu.cli.load_document", return_value="text") as loader:
            self.assertEqual(main(["--", "-source.py"]), 0)
            loader.assert_called_once_with("-source.py")

    def test_propagates_the_apps_exit_status(self):
        self.app_factory.return_value.return_code = 1
        self.assertEqual(main([str(self.path)]), 1)

    def test_game_options_select_forest_by_default_and_support_reveal(self):
        self.assertEqual(main([str(self.path), "--game", "--reveal", "--seed", "pond"]), 0)
        self.game_factory.assert_called_once_with(
            "    [bold]\n\\x1b[31m", theme="forest", reveal=True,
            light_settings=LightSettings(16.0, 2.0), seed="pond")
        self.app_factory.assert_not_called()
        self.game_factory.return_value.run.assert_called_once_with()

    def test_game_accepts_explicit_moonlight_and_reveal_requires_game(self):
        self.assertEqual(main([str(self.path), "--game", "--theme", "moonlight", "--radius", "20"]), 0)
        self.assertEqual(self.game_factory.call_args.kwargs["theme"], "moonlight")
        self.assertEqual(self.game_factory.call_args.kwargs["light_settings"], LightSettings(20, 2))
        with patch("nilavu.cli.load_document") as loader:
            with self.assertRaises(SystemExit) as exit_status:
                main([str(self.path), "--reveal"])
            self.assertEqual(exit_status.exception.code, 2)
            loader.assert_not_called()
