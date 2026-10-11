# Nilavu

A quiet terminal game about finding fireflies and bringing them home.
Explore a seeded ASCII landscape of woodland, flowers, ruins, crystals, and
water, lit by a movable light and small object glows. Wake three fireflies,
let them follow you, and gather at the pond to reveal the whole landscape.

Nilavu also includes a read-only source viewer with the same lighting effect.
Version **0.1.0** is an early release; scenery and discovery balance are still
being refined.

## Install and play

Requires **Python 3.11+**, Git, and an interactive terminal. RGB color support
is recommended. Nilavu uses your terminal's font and runs in the current window.

Clone the repository, then install into a virtual environment.

### macOS / Linux

```sh
git clone https://github.com/jonathan-16bit/nilavu.git
cd nilavu
python3 -m venv .venv
.venv/bin/python -m pip install .
./dev run --game --seed fern
```

### Windows (PowerShell)

```powershell
git clone https://github.com/jonathan-16bit/nilavu.git
cd nilavu
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install .
.venv\Scripts\nilavu.exe --game --seed fern
```

The examples below use `./dev run`. On Windows, use
`.venv\Scripts\nilavu.exe` in its place. With the virtual environment activated,
you can use `nilavu` directly on either platform.

## How to play

1. Explore with WASD, arrow keys, or `hjkl`. Look for bright white `i` fireflies.
2. Move close and press **Space** when the top border says `Space: wake`.
   Each awakened firefly joins you; the border tracks your progress.
3. Once all three are awake, follow the top border's compass directions toward
   the teal **`G`** marker on the pond's west bank. `G: NE` means northeast.
4. Near the marker, press **Space** when prompted to gather. The fireflies settle
   beside the water and the landscape lights up over two seconds.

Stay and explore the revealed world, or press `r` for a fresh run.
There are no enemies or time limits. Visiting the pond early preserves progress
and tells you how many fireflies remain.

Water, tree trunks, rocks, crystals, and ruin walls block movement. Flowers,
foliage, ground, and stepping stones are walkable. The world is **180 × 48
cells**; smaller terminals scroll as you move. A terminal of at least 182 columns
by 50 rows fits the entire map. Resizing or changing font size changes how much
you see, without enlarging the world.

## Controls

| Key | Action |
| --- | --- |
| WASD, arrow keys, or `hjkl` | Move. |
| Space | Wake a nearby firefly or gather at the pond marker (game only). |
| `t` | Switch between forest and moonlight colors. |
| `r` | Game: start the next seeded world. Viewer: advance the forest palette seed. |
| `q` | Quit. |

In the game, `r` resets progress in either theme. Changing themes or resizing
preserves progress. In the viewer, `r` works only in forest; palette changes
preserve your position.

## Seeds and appearance

```sh
./dev run --game --seed violet-after-rain
./dev run --game --theme moonlight --radius 18
```

A seed is any text string, including hex-looking strings such as `7fa3`.
In the game, it determines the terrain, scenery details, and firefly positions.
The same seed recreates the same starting world in this version; future generator
changes may alter it. `r` follows a repeatable sequence of seeds. Reuse the seed
shown in the bottom border with `--seed` to return to its starting world.

**Forest** uses seeded green and gold colors. **Moonlight** uses a fixed cool
palette. Switching themes changes colors without changing the game map.
Lighting uses five shading levels, with subtle lantern, crystal, and water
animation. Character appearance depends on your terminal font.

| Option | Default | Effect |
| --- | --- | --- |
| `--seed TEXT` | `moss` | Starting world seed, or forest palette seed in the viewer. |
| `--theme NAME` | `forest` game; `moonlight` viewer | Choose `forest` or `moonlight`. |
| `--radius NUMBER` | `16` game; `12` viewer | Light radius in terminal column widths. |
| `--cell-aspect-ratio NUMBER` | `2` | Cell height divided by width; tune this if the light looks oval. |
| `--reveal` | Off | Start with the whole map lit for inspection (game only). |

Radius and aspect ratio must be finite positive numbers. Use
`./dev run --help` for all command-line options.

## Source viewer

Supply a local file instead of `--game`:

```sh
./dev run pyproject.toml
./dev run src/nilavu/palette.py --theme forest --seed fern
```

Move the light over the text using the same movement keys. Long files and wide
lines scroll automatically. In this mode, seeds affect the forest palette,
not the document. `./dev run` without arguments opens Nilavu's palette source
for a quick demo.

The viewer reads regular UTF-8 files up to **1 MiB** without modifying them.
Invalid UTF-8 and NUL-containing files are rejected. Tabs expand to four-column
stops, and terminal controls and invisible formatting characters are displayed
as escape notation. Source is rendered as literal text, never executed or parsed
as markup. Unicode widths can vary between terminal fonts.

## Development

For local code changes, install in editable mode and run the tests:

```sh
.venv/bin/python -m pip install -e .
./dev test
```

On Windows, use `.venv\Scripts\python.exe -m pip install -e .` and
`.venv\Scripts\python.exe -m unittest discover -s tests`.
`./dev help` lists the repository shortcuts.

## Scope and privacy

The game uses a fixed-size world, and runs and settings are not saved.
The source viewer is read-only and has no syntax highlighting.

Game mode requires no input file. Neither mode uses runtime networking or
subprocess execution. Inherited Textual diagnostic logging, debug features,
developer-tool connections, and automatic screenshots are disabled.

## License

[MIT](LICENSE).
