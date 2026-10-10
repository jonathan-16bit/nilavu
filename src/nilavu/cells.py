"""Map prepared text to terminal columns using the renderer's width rules."""

from collections.abc import Iterator

from rich.cells import cell_len, get_character_cell_size


def line_width(text: str) -> int:
    """Measure a line, reserving a base space for leading combining marks."""
    return cell_len(text) + int(bool(text) and get_character_cell_size(text[0]) == 0)


def visible_cells(text: str, start: int, width: int) -> Iterator[tuple[int, str, int]]:
    """Yield (document column, text, cell width) for a padded visible row.

    A glyph and its trailing zero-width marks are styled together. Wide glyphs
    cut by a viewport edge become spaces rather than corrupting adjacent cells.
    """
    end = start + width
    column = 0
    index = 0
    while index < len(text) and column < end:
        stop = index + 1
        while stop < len(text) and get_character_cell_size(text[stop]) == 0:
            stop += 1
        glyph = text[index:stop]
        # A leading mark has no base character. Supply a display-only space so
        # it cannot attach to a previous row or escape our column accounting.
        if get_character_cell_size(glyph[0]) == 0:
            glyph = " " + glyph
        cells = cell_len(glyph)
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
