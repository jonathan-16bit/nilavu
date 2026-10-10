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

From the repository, run in your existing terminal. `./dev run` without arguments
opens Nilavu's palette source file for a quick playground; supply any local code
or text file to explore something else:

```bash
./dev run
./dev run pyproject.toml
```

Use `h`, `j`, `k`, `l` or the arrow keys to move left, down, up, and right.
Press `q` to exit. Long files and wide lines scroll when the light approaches a
screen edge. Movement stays within the document's rectangular bounds, including
empty space beside short lines.

Adjust the light when launching:

```bash
./dev run pyproject.toml --radius 14 --cell-aspect-ratio 1.8
```

| Option | Default | Meaning |
| --- | --- | --- |
| `--radius` | `12` | Reach in terminal column-width units. Larger values expand the light. |
| `--cell-aspect-ratio` | `2` | Cell height divided by width. Larger values compress the vertical reach. |

Choose a coordinated text, cell-background, darkness, and cursor palette:

```bash
./dev run pyproject.toml --theme moonlight
./dev run pyproject.toml --theme forest --seed fern --radius 14
```

`--theme` accepts `moonlight` (the default, cool blue) or `forest` (seeded greens
with a gold cursor). Forest generates one coordinated palette for the whole
view. `--seed` accepts text and defaults to `moss`: the same seed repeats the same
colors, while different seeds vary them within forest color ranges. It is ignored
for moonlight. Both themes keep the same five shading levels and movement;
the border continues to use your terminal's colors.

Radius and aspect ratio accept finite positive numbers, including decimals.
Lighting and scrolling use the same settings. Scrolling margins shrink on small screens;
document boundaries can still clip the light. Tune the aspect ratio to suit your
terminal font rather than assuming every terminal has the same cell shape.

See all options with `./dev run --help`. The launcher uses the existing virtual
environment automatically. You can also activate it with `source .venv/bin/activate` and use `nilavu` directly.

## Input handling and current limits

- Opens only the supplied local file, read-only. The viewer has no runtime
  network access or subprocess execution.
- Accepts regular UTF-8 files up to 1 MiB. Invalid UTF-8 and NUL-containing files
  are rejected.
- Normalizes line endings, expands tabs at four-column stops, and displays
  terminal controls and invisible formatting characters as escape notation.
  File contents are displayed as literal text, never interpreted as markup.
- Navigation counts terminal columns. Wide glyphs receive one style across both
  columns, and combining marks stay with their base glyph. Partial wide glyphs
  at viewport edges become spaces until the full glyph is visible. Actual glyph
  widths can vary between terminal fonts.
- Provides a fixed moonlight palette and a seeded forest palette. There is no
  scenery or map generation, syntax highlighting, file editing, saved
  configuration, or settings UI. CLI settings apply to the current launch only.

## Tests

```bash
./dev test
./dev test -v
```

`./dev help` lists development shortcuts. The `dev` script uses a POSIX shell
(macOS/Linux). On Windows, use the commands directly:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests
.venv\Scripts\nilavu.exe pyproject.toml
```

## License

MIT; see [LICENSE](LICENSE).
