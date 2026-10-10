# Nilavu

Nilavu is a terminal source viewer with a movable light. Nearby text and cells
brighten through five shading levels, while distant text fades into darkness.
Source stays real terminal text, with a visible cursor and scrolling that follows
the illuminated area. A thin border uses your terminal's default foreground and
background colors and resizes with the window, reserving one cell on each edge.

This is an early development version.

## Setup

Requires Python 3.11 or newer and an interactive terminal. A terminal with RGB
color support gives the intended appearance; fonts and glyph rendering come from
your terminal.

From the repository directory, create a virtual environment and install locally:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

These commands use macOS/Linux paths. On Windows, use `.venv\Scripts\python.exe`
and `.venv\Scripts\nilavu.exe` instead of the corresponding `.venv/bin` paths.

## Use

Run in your existing terminal:

```bash
.venv/bin/nilavu pyproject.toml
```

Use `h`, `j`, `k`, `l` or the arrow keys to move left, down, up, and right.
Press `q` to exit. Long files and wide lines scroll when the light approaches a
screen edge. Movement stays within the document's rectangular bounds, including
empty space beside short lines.

Adjust the light when launching:

```bash
.venv/bin/nilavu pyproject.toml --radius 14 --cell-aspect-ratio 1.8
```

| Option | Default | Meaning |
| --- | --- | --- |
| `--radius` | `12` | Reach in terminal column-width units. Larger values expand the light. |
| `--cell-aspect-ratio` | `2` | Cell height divided by width. Larger values compress the vertical reach. |

Both options accept finite positive numbers, including decimals. Lighting and
scrolling use the same settings. Scrolling margins shrink on small screens;
document boundaries can still clip the light. Tune the aspect ratio to suit your
terminal font rather than assuming every terminal has the same cell shape.

See all options with `.venv/bin/nilavu --help`. You can also launch with
`.venv/bin/python -m nilavu pyproject.toml`.

## Input handling and current limits

- Opens only the supplied local file, read-only. The viewer has no runtime
  network access or subprocess execution.
- Accepts regular UTF-8 files up to 1 MiB. Invalid UTF-8 and NUL-containing files
  are rejected.
- Normalizes line endings, expands tabs at four-character stops, and displays
  terminal controls and invisible formatting characters as escape notation.
  File contents are displayed as literal text, never interpreted as markup.
- Navigation counts terminal columns. Wide glyphs receive one style across both
  columns, and combining marks stay with their base glyph. Partial wide glyphs
  at viewport edges become spaces until the full glyph is visible. Actual glyph
  widths can vary between terminal fonts; tab expansion still counts text
  characters rather than terminal columns.
- Uses one fixed palette. There is no syntax highlighting, file editing, saved
  configuration, or settings UI. CLI settings apply to the current launch only.

## Tests

```bash
.venv/bin/python -m unittest discover -s tests
```

## License

MIT; see [LICENSE](LICENSE).
