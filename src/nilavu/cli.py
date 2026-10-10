"""Connect command-line arguments, safe file loading, and the terminal UI."""

import argparse
from collections.abc import Sequence
import sys
from typing import TextIO

from nilavu.app import NilavuApp
from nilavu.document import DocumentError, load_document, normalize_text


class _SafeArgumentParser(argparse.ArgumentParser):
    """Keep even invalid command-line arguments from emitting raw controls."""

    def _print_message(self, message: str | None, file: TextIO | None = None) -> None:
        # argparse includes unknown arguments in errors. A filename or argument
        # can contain the same unsafe controls as file contents.
        if message:
            super()._print_message(normalize_text(message), file)


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
            "Move with hjkl or arrow keys. Press q to quit."
        ),
    )
    # Newer Python versions can color help. Keep help plain before sanitizing it;
    # setting this attribute is harmless on older versions without colored help.
    parser.color = False
    parser.add_argument("path", help="path to a UTF-8 source or text file")
    arguments = parser.parse_args(argv)

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

    app = NilavuApp(source_text)
    app.run()
    return app.return_code
