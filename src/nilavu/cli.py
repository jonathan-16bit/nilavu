"""Connect command-line arguments, safe file loading, and the terminal UI."""

import argparse
import math
from collections.abc import Sequence
import sys
from typing import TextIO

from nilavu.app import NilavuApp
from nilavu.document import DocumentError, load_document, normalize_text
from nilavu.game import ForestApp
from nilavu.lighting import DEFAULT_LIGHT_SETTINGS, LightSettings
from nilavu.palette import DEFAULT_SEED, DEFAULT_THEME, THEMES


class _SafeArgumentParser(argparse.ArgumentParser):
    """Keep even invalid command-line arguments from emitting raw controls."""

    def _print_message(self, message: str | None, file: TextIO | None = None) -> None:
        # argparse includes unknown arguments in errors. A filename or argument
        # can contain the same unsafe controls as file contents.
        if message:
            super()._print_message(normalize_text(message), file)


def _positive_finite(value: str) -> float:
    """Convert a geometry option before any file loading or terminal takeover."""
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a finite positive number") from None
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a finite positive number")
    return number


def main(argv: Sequence[str] | None = None) -> int:
    """Launch the viewer, returning 0 on success or 1 on a loading/terminal error.

    argparse handles help with exit status 0 and argument errors with status 2.
    Passing argv explicitly makes the same flow testable without changing the
    process arguments; None uses the arguments supplied by the shell.
    """
    parser = _SafeArgumentParser(
        prog="nilavu",
        description=(
            "View a local source file through a movable light. "
            "Move with hjkl or arrow keys. Press t to switch themes, "
            "r for the next seed (a new world in --game). Press q to quit."
        ),
    )
    # Newer Python versions can color help. Keep help plain before sanitizing it;
    # setting this attribute is harmless on older versions without colored help.
    parser.color = False
    parser.add_argument("path", help="path to a UTF-8 source or text file")
    parser.add_argument("--game", action="store_true", help="explore an experimental 120x40 forest")
    parser.add_argument("--reveal", action="store_true", help="show the whole forest (requires --game)")
    parser.add_argument(
        "--theme",
        choices=THEMES,
        default=None,
        help="palette (default: moonlight for the viewer, forest for --game)",
    )
    parser.add_argument(
        "--seed",
        default=DEFAULT_SEED,
        help="starting palette/world seed (default: %(default)s)",
    )
    parser.add_argument(
        "--radius",
        type=_positive_finite,
        default=DEFAULT_LIGHT_SETTINGS.radius,
        metavar="NUMBER",
        help="light radius in terminal columns (default: %(default)s)",
    )
    parser.add_argument(
        "--cell-aspect-ratio",
        type=_positive_finite,
        default=DEFAULT_LIGHT_SETTINGS.cell_aspect_ratio,
        metavar="NUMBER",
        help="cell height divided by width (default: %(default)s)",
    )
    arguments = parser.parse_args(argv)
    if arguments.reveal and not arguments.game:
        parser.error("--reveal requires --game")
    # Keep one immutable settings object throughout the UI so illumination and
    # scrolling cannot accidentally use different geometry.
    try:
        light_settings = LightSettings(arguments.radius, arguments.cell_aspect_ratio)
    except ValueError as error:
        parser.error(str(error))

    # All file validation happens before Textual enters full-screen mode.
    try:
        source_text = load_document(arguments.path)
    except DocumentError as error:
        print(f"nilavu: {error}", file=sys.stderr)
        return 1

    # Redirected input cannot deliver keys; redirected output is not a screen.
    # Help and loading errors remain usable without an interactive terminal.
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print(
            "nilavu: an interactive terminal is required on stdin and stdout.",
            file=sys.stderr,
        )
        return 1

    settings = dict(light_settings=light_settings, seed=arguments.seed)
    if arguments.game:
        app = ForestApp(source_text, theme=arguments.theme or "forest",
                        reveal=arguments.reveal, **settings)
    else:
        app = NilavuApp(source_text, theme=arguments.theme or DEFAULT_THEME, **settings)
    app.run()
    return app.return_code
