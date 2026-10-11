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

| Key | Action |
| --- | --- |
| `h`, `j`, `k`, `l` / arrow keys | Move left, down, up, and right. |
| `t` | Switch between moonlight and forest, remembering the forest seed. |
| `r` | Advance to the next forest seed; does nothing in moonlight. |
| `q` | Quit and restore the terminal. |

The bottom border shows the theme and, for forest, the current seed. Long files
and wide lines scroll when the light approaches a screen edge. Movement stays
within the document's rectangular bounds, including empty space beside short lines.
Changing themes or seeds preserves the light position and scroll position.

Configure the viewer when launching:

```bash
./dev run pyproject.toml --radius 14 --cell-aspect-ratio 1.8
```

| Option | Default | Meaning |
| --- | --- | --- |
| `--theme` | `moonlight` | Starting palette family: `moonlight` or `forest`. |
| `--seed` | `moss` | Starting forest seed, remembered even when launching in moonlight. |
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
colors, while different seeds vary them within forest color ranges. Moonlight
uses fixed colors and remembers your forest seed when you switch back.

Seeds are text strings: `fern`, `12345`, and `7fa3` are all valid. Hex-looking
strings are treated as text, not as base colors. The seed selects colors within
the forest family's green and gold ranges; it does not depend on file contents.
Using the same seed on another file gives the same palette. Different seeds
can produce the same colors, so uniqueness is not guaranteed.

While forest is active, `r` uses SHA-256 to hash the current seed into the next
eight-character hexadecimal seed and applies its palette. Starting from the same seed repeats
the same sequence; `r` does nothing in moonlight. Reuse any seed shown in the
border with `--seed` to reproduce that palette and continue its sequence. Long
status text is clipped to fit small terminals; control and non-ASCII characters
in manually supplied seeds appear as escape notation.

Both themes keep the same five shading levels and movement; the border continues
to use your terminal's colors.

Radius and aspect ratio accept finite positive numbers, including decimals.
Lighting and scrolling use the same settings. Scrolling margins shrink on small screens;
document boundaries can still clip the light. Tune the aspect ratio to suit your
terminal font rather than assuming every terminal has the same cell shape.

See all options with `./dev run --help`. The launcher uses the existing virtual
environment automatically. You can also activate it with
`source .venv/bin/activate` and use `nilavu` directly.

## Forest experiment

```bash
./dev run src/nilavu/palette.py --game --seed fern
./dev run src/nilavu/palette.py --game --seed fern --reveal
```

`--game` opens a fixed **140-column by 32-row** woodland with moss, grass,
earthy clearings, spaced groves, flowers, and a pond. Most ground and foliage
are walkable; water and tree cores block movement. Use the same movement keys
and `q` to quit.
This is a terrain experiment: fireflies, Space interactions, followers, and the
pond finale are not implemented yet.

The world has its own terminal-colored border. A terminal at least 142 columns
by 34 rows displays the whole world; larger terminals center it in neutral space,
and smaller terminals scroll. Changing font size or resizing changes only the
viewport, never the generated world or movement bounds.

Source characters form leafy canopy clusters, trunk cores, pond ripples, and
small flower patches. Ordinary moss, grass, and clearings have blank text cells
to keep walkable ground uncluttered. Warm wood colors distinguish tree cores
from muted clearings. Each scenery role has its own foreground color;
both text and backgrounds respond to the same five lighting levels. Terrain and
placement come from the seed, independently of source-file formatting or meaning.
Short input is reused; long input is sampled across the file. Sampled words and
combining sequences are bounded, and wide glyphs only occupy matching terrain
cells. Empty input still produces colored terrain. The input file is read-only.
The same file and seed reproduce the same world.

Game mode starts with the forest palette unless `--theme` is supplied. `t`
changes colors without changing terrain; `r` advances the seed and starts a new
world at its initial clearing, in either theme. `--reveal` lights the entire world
for inspecting its composition, while leaving collisions active. It requires
`--game` and is an experiment preview, not a completed game.

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
- Provides a source viewer and an experimental generated forest, using fixed
  moonlight or seeded forest colors. There is no syntax highlighting, file
  editing, saved configuration, or settings UI. Settings apply to the current
  launch only.

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
