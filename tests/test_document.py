"""Behavior checks for file loading and terminal-safe text preparation."""

from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from nilavu.document import DocumentError, MAX_INPUT_BYTES, load_document, normalize_text


class NormalizeTextTests(unittest.TestCase):
    def test_preserves_printable_unicode_and_markup_as_literal_text(self):
        text = "[bold]நிலவு café e\u0301 🌙[/bold]\n"
        self.assertEqual(normalize_text(text), text)

    def test_normalizes_line_endings_without_losing_blank_lines(self):
        self.assertEqual(normalize_text("one\r\n\r\ntwo\rthree\n"), "one\n\ntwo\nthree\n")

    def test_tabs_advance_to_four_column_stops_on_each_line(self):
        self.assertEqual(normalize_text("\tx\nx\ty\n1234\tz"), "    x\nx   y\n1234    z")

    def test_escapes_terminal_sequences_and_non_newline_controls(self):
        # Exercise color changes and a clipboard-command sequence as inert text.
        text = "\x1b[31mred\x1b[0m\x1b]52;c;payload\x07\x08\x7f\x9b"
        expected = r"\x1b[31mred\x1b[0m\x1b]52;c;payload\x07\x08\x7f\x9b"
        self.assertEqual(normalize_text(text), expected)

    def test_escapes_unicode_formatting_and_surrogates(self):
        self.assertEqual(
            normalize_text("a\u202eb\u200b\ud800\U000e0001"),
            r"a\u202eb\u200b\ud800\U000e0001",
        )

    def test_all_c0_and_c1_controls_are_neutralized_except_newlines(self):
        text = "".join(chr(value) for value in (*range(32), *range(127, 160)))
        result = normalize_text(text)
        self.assertTrue(
            all(character == "\n" or ord(character) >= 32 for character in result)
        )
        self.assertFalse(any(127 <= ord(character) <= 159 for character in result))


class LoadDocumentTests(unittest.TestCase):
    def setUp(self):
        # Each test gets disposable input files, never a real project source file.
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "source.py"

    def test_reads_prepares_and_preserves_source_bytes(self):
        content = "\tprint('நிலவு')\r\n\x1b[31m[bold]".encode("utf-8")
        self.path.write_bytes(content)
        self.assertEqual(load_document(self.path), "    print('நிலவு')\n\\x1b[31m[bold]")
        self.assertEqual(self.path.read_bytes(), content)

    def test_accepts_empty_file_and_string_path(self):
        self.path.write_bytes(b"")
        self.assertEqual(load_document(str(self.path)), "")

    def test_rejects_missing_path(self):
        with self.assertRaisesRegex(DocumentError, "does not exist"):
            load_document(self.path)

    def test_reports_invalid_path(self):
        with self.assertRaisesRegex(DocumentError, "path contains a NUL"):
            load_document("invalid\x00name")

    def test_rejects_directory(self):
        with self.assertRaisesRegex(DocumentError, "regular file"):
            load_document(self.directory.name)

    def test_rejects_non_regular_file_before_opening(self):
        # Simulate a pipe without creating or opening a potentially blocking one.
        with (
            patch.object(Path, "stat") as file_stat,
            patch("nilavu.document.os.open") as file_open,
        ):
            file_stat.return_value.st_mode = 0o010000  # FIFO file type.
            with self.assertRaisesRegex(DocumentError, "regular file"):
                load_document(self.path)
            file_open.assert_not_called()

    def test_reports_permission_and_read_errors(self):
        self.path.write_bytes(b"text")
        # Simulate failures because chmod-based permission tests depend on who
        # runs the suite (an administrator may still be able to read the file).
        for error, message in (
            (PermissionError(), "permission denied"),
            (OSError(), "could not be read"),
        ):
            with self.subTest(error=type(error).__name__):
                with patch("nilavu.document.os.open", side_effect=error):
                    with self.assertRaisesRegex(DocumentError, message):
                        load_document(self.path)

    def test_accepts_exact_size_limit(self):
        self.path.write_bytes(b"a" * MAX_INPUT_BYTES)
        self.assertEqual(len(load_document(self.path)), MAX_INPUT_BYTES)

    def test_rejects_oversized_file_before_opening(self):
        self.path.write_bytes(b"a" * (MAX_INPUT_BYTES + 1))
        with patch("nilavu.document.os.open") as file_open:
            with self.assertRaisesRegex(DocumentError, "size limit"):
                load_document(self.path)
            file_open.assert_not_called()

    @unittest.skipUnless(
        hasattr(os, "mkfifo") and hasattr(os, "O_NONBLOCK"),
        "requires named pipes and non-blocking open",
    )
    def test_rejects_fifo_swapped_after_stat_without_blocking_and_closes_descriptor(self):
        self.path.write_bytes(b"text")
        fifo = Path(self.directory.name) / "fifo"
        os.mkfifo(fifo)
        original_stat = Path.stat
        original_open = os.open
        descriptors = []

        def swap_after_stat(path, *args, **kwargs):
            info = original_stat(path, *args, **kwargs)
            if path == self.path:
                os.replace(fifo, self.path)
            return info

        def guarded_open(path, flags, *args, **kwargs):
            # Fail before touching the FIFO if a regression removes the flag;
            # this keeps the test deterministic instead of hanging the suite.
            self.assertTrue(flags & os.O_NONBLOCK)
            descriptor = original_open(path, flags, *args, **kwargs)
            descriptors.append(descriptor)
            return descriptor

        with (
            patch.object(Path, "stat", swap_after_stat),
            patch("nilavu.document.os.open", guarded_open),
        ):
            with self.assertRaisesRegex(DocumentError, "regular file"):
                load_document(self.path)
        self.assertEqual(len(descriptors), 1)
        with self.assertRaises(OSError):
            os.fstat(descriptors[0])

    def test_bounded_read_rejects_growth_after_stat(self):
        self.path.write_bytes(b"a" * (MAX_INPUT_BYTES + 2))
        actual_stat = self.path.stat()
        # Report an earlier small size but read the real oversized file. This
        # models growth deterministically, without threads or timing assumptions.
        with patch.object(Path, "stat") as file_stat:
            file_stat.return_value.st_mode = actual_stat.st_mode
            file_stat.return_value.st_size = 0
            with self.assertRaisesRegex(DocumentError, "size limit"):
                load_document(self.path)

    def test_rejects_nul_containing_and_invalid_utf8_input(self):
        for content, message in ((b"hello\x00world", "binary"), (b"\xff\xfe", "UTF-8")):
            with self.subTest(content=content):
                self.path.write_bytes(content)
                with self.assertRaisesRegex(DocumentError, message):
                    load_document(self.path)
