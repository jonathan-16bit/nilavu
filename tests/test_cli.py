"""Check CLI behavior without taking over the test runner's terminal."""

import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from nilavu.cli import main


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

    def test_loads_and_prepares_the_supplied_path_before_launch(self):
        self.assertEqual(main([str(self.path)]), 0)
        self.app_factory.assert_called_once_with("    [bold]\n\\x1b[31m")
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
