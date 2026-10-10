"""Read local text files and prepare their contents for safe display."""

import os
from pathlib import Path
import stat
import unicodedata

from nilavu.cells import expand_tabs


# Bound raw input before decoding so accidental huge files cannot exhaust memory.
MAX_INPUT_BYTES = 1024 * 1024
TAB_WIDTH = 4


class DocumentError(ValueError):
    """A predictable loading failure that a future CLI can report to the user."""


def _nonblocking_opener(path: str, flags: int) -> int:
    """Open without waiting for a FIFO writer on platforms with O_NONBLOCK."""
    # The path can change after stat. Non-blocking open lets us reject a swapped
    # FIFO with fstat before reading it. Regular-file reads remain unchanged.
    # O_NOCTTY also prevents a swapped terminal device becoming our controlling
    # terminal. Missing flags contribute zero on platforms without these APIs.
    flags |= getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOCTTY", 0)
    return os.open(path, flags)


def normalize_text(text: str) -> str:
    """Normalize newlines, escape controls, and expand four-column tabs.

    Printable Unicode is preserved. Unicode control, format, and surrogate
    characters become visible escape notation, including ANSI escape bytes
    and invisible bidirectional formatting characters.
    """
    # Replace CRLF first so a Windows newline does not become two newlines.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    characters = []
    for character in text:
        # Keep structural whitespace until the final tab expansion. Cc means
        # control, Cf means invisible formatting, and Cs means surrogate.
        if character not in ("\n", "\t") and unicodedata.category(character) in (
            "Cc",
            "Cf",
            "Cs",
        ):
            # Literal backslash notation reveals the original value without
            # sending an executable control character to the terminal.
            codepoint = ord(character)
            if codepoint <= 0xFF:
                characters.append(f"\\x{codepoint:02x}")
            elif codepoint <= 0xFFFF:
                characters.append(f"\\u{codepoint:04x}")
            else:
                characters.append(f"\\U{codepoint:08x}")
        else:
            characters.append(character)
    # Expand after escaping so tabs align with the visible escape notation.
    # Use the renderer's cell widths: a wide glyph takes two columns, while a
    # combining mark shares its base column. Newlines reset the tab stops.
    return expand_tabs("".join(characters), TAB_WIDTH)


def load_document(path: str | Path) -> str:
    """Read a regular UTF-8 file of at most 1 MiB and return safe text.

    NUL-containing input is rejected as binary. The file is opened read-only;
    a bounded read also protects against growth after the initial size check.
    """
    path = Path(path)
    if "\x00" in str(path):
        raise DocumentError("Input path contains a NUL character.")
    try:
        # Check metadata before opening: directories and special files such as
        # pipes are not source documents, and opening a pipe may block.
        file_info = path.stat()
        if not stat.S_ISREG(file_info.st_mode):
            raise DocumentError("Input must be a regular file.")
        if file_info.st_size > MAX_INPUT_BYTES:
            raise DocumentError("Input exceeds the 1 MiB size limit.")

        # Binary mode leaves decoding and newline policy under our control.
        # open owns the descriptor returned by our opener and closes it even
        # when the post-open validation rejects a changed file type.
        with open(path, "rb", opener=_nonblocking_opener) as source:
            # Inspect the opened file too: the path may have changed since stat.
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise DocumentError("Input must be a regular file.")
            # One extra byte distinguishes an exactly full file from an oversized
            # one, even when it grew after the metadata check.
            content = source.read(MAX_INPUT_BYTES + 1)
    except FileNotFoundError as error:
        raise DocumentError("Input file does not exist.") from error
    except PermissionError as error:
        raise DocumentError("Input file cannot be read: permission denied.") from error
    except OSError as error:
        raise DocumentError("Input file could not be read.") from error

    if len(content) > MAX_INPUT_BYTES:
        raise DocumentError("Input exceeds the 1 MiB size limit.")
    # NUL is valid UTF-8 but is a useful signal that input is binary, not source.
    if b"\x00" in content:
        raise DocumentError("Input contains NUL bytes and appears to be binary.")
    try:
        # Strict decoding rejects malformed bytes instead of silently replacing
        # them and presenting a misleading version of the source.
        text = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise DocumentError("Input must be valid UTF-8 text.") from error
    return normalize_text(text)
