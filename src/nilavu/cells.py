"""Map prepared text to terminal columns using the renderer's width rules."""

from bisect import bisect_right
from collections.abc import Iterator

from rich.cells import cell_len, get_character_cell_size


def line_width(text: str) -> int:
    """Measure a line, reserving a base space for leading combining marks."""
    return cell_len(text) + int(bool(text) and get_character_cell_size(text[0]) == 0)


def expand_tabs(text: str, tab_width: int) -> str:
    """Expand tabs to terminal-column stops, resetting at each newline."""
    lines = []
    for line in text.split("\n"):
        pieces = line.split("\t")
        parts = [pieces[0]]
        column = line_width(pieces[0])
        for piece in pieces[1:]:
            spaces = tab_width - column % tab_width
            parts.extend((" " * spaces, piece))
            # Each piece is measured once. Measuring the entire accumulated line
            # at every tab would make tab-heavy files increasingly expensive.
            column += spaces + cell_len(piece)
        lines.append("".join(parts))
    return "\n".join(lines)


def visible_cells(text: str, start: int, width: int) -> Iterator[tuple[int, str, int]]:
    """Yield (document column, text, cell width) for a padded visible row.

    A glyph and its trailing zero-width marks are styled together. Wide glyphs
    cut by a viewport edge become spaces rather than corrupting adjacent cells.
    """
    # Prepared ASCII has one character per cell. Python records whether a string
    # is ASCII, so this path can jump to a column without scanning the prefix.
    if text.isascii():
        for column in range(start, start + width):
            yield column, text[column] if column < len(text) else " ", 1
        return
    yield from _scan_visible_cells(text, start, width, 0, 0)


def _glyph_at(text: str, index: int) -> tuple[int, str, int]:
    """Read one glyph and its combining marks from a known string boundary."""
    stop = index + 1
    while stop < len(text) and get_character_cell_size(text[stop]) == 0:
        stop += 1
    glyph = text[index:stop]
    # A leading mark has no base character. Supply a display-only space so
    # it cannot attach to a previous row or escape our column accounting.
    if get_character_cell_size(glyph[0]) == 0:
        glyph = " " + glyph
    return stop, glyph, cell_len(glyph)


def _scan_visible_cells(
    text: str, start: int, width: int, column: int, index: int
) -> Iterator[tuple[int, str, int]]:
    """Render from a glyph boundary, possibly before a partially visible glyph."""
    end = start + width
    while index < len(text) and column < end:
        stop, glyph, cells = _glyph_at(text, index)
        if column + cells > start:
            if column >= start and column + cells <= end:
                yield column, glyph, cells
            else:
                for clipped in range(max(start, column), min(end, column + cells)):
                    yield clipped, " ", 1
        column += cells
        index = stop
    for padded in range(max(start, column), end):
        yield padded, " ", 1


class CellIndex:
    """Sparse column-to-string checkpoints for an immutable Unicode line."""

    def __init__(self, text: str) -> None:
        self._text = text
        columns = [0]
        offsets = [0]
        column = index = 0
        while index < len(text):
            # Checkpoints always fall at glyph boundaries. One per roughly 256
            # columns bounds rescanning without storing an entry for every cell.
            if column - columns[-1] >= 256:
                columns.append(column)
                offsets.append(index)
            index, _, cells = _glyph_at(text, index)
            column += cells
        # An end checkpoint makes padding past a short line constant-time too.
        columns.append(column)
        offsets.append(index)
        self._columns = tuple(columns)
        self._offsets = tuple(offsets)

    def visible_cells(self, start: int, width: int) -> Iterator[tuple[int, str, int]]:
        """Find the nearest earlier checkpoint, then render only nearby glyphs."""
        checkpoint = bisect_right(self._columns, start) - 1
        yield from _scan_visible_cells(
            self._text,
            start,
            width,
            self._columns[checkpoint],
            self._offsets[checkpoint],
        )
