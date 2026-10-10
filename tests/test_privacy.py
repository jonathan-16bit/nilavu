"""Exercise framework failures and inherited screenshot settings safely."""

from contextlib import redirect_stderr
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rich.text import Text
from textual import constants

from nilavu.app import NilavuApp


class PrivacyTests(unittest.IsolatedAsyncioTestCase):
    async def test_display_errors_hide_source_and_preserve_original_failure(self):
        marker = "PRIVATE_DOCUMENT_SENTINEL"

        class RichError(RuntimeError):
            def __rich__(self):
                return Text(marker)

        for error in (RuntimeError(marker), RichError(marker)):
            with self.subTest(error_type=type(error).__name__):
                class FailingApp(NilavuApp):
                    def on_mount(self):
                        source_text = self._source_text
                        raise error

                stderr = io.StringIO()
                with redirect_stderr(stderr):
                    app = FailingApp(marker)
                    with self.assertRaises(type(error)) as raised:
                        async with app.run_test():
                            pass
                self.assertIs(raised.exception, error)
                self.assertEqual(app.return_code, 1)
                self.assertIn("unexpected display error", stderr.getvalue())
                self.assertIn(type(error).__name__, stderr.getvalue())
                self.assertNotIn(marker, stderr.getvalue())

    async def test_inherited_screenshot_setting_does_not_save_or_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            screenshot = Path(directory) / "source.svg"
            # Textual reads its environment into constants at import time.
            # Use a short timer so the framework's default behavior would fire.
            with (
                patch.object(constants, "SCREENSHOT_DELAY", 0.01),
                patch.object(constants, "SCREENSHOT_LOCATION", directory),
                patch.object(constants, "SCREENSHOT_FILENAME", screenshot.name),
            ):
                app = NilavuApp("private source")
                async with app.run_test() as pilot:
                    await pilot.pause(0.05)
                    self.assertFalse(screenshot.exists())
                    await pilot.press("l")
                    self.assertEqual(app.light_position.x, 1)
                    await pilot.press("q")
                self.assertEqual(app.return_code, 0)
