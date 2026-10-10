"""Display prepared source text inside the current terminal."""

from textual.app import App, ComposeResult
from textual.widgets import Static


class NilavuApp(App[None], inherit_bindings=False):
    """A minimal full-screen viewer for text returned by load_document().

    File loading stays outside the UI: callers validate and prepare the source
    before constructing the app, so a loading error cannot take over the screen.
    """

    # Keep the first screen focused on source text, without framework menus or
    # extra shortcuts. The built-in quit action handles terminal cleanup.
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [("q", "quit", "Quit")]

    # ANSI default colors let the terminal supply its own foreground/background.
    # A screen-sized widget clips long lines and extra rows without scrolling.
    CSS = """
    Screen {
        background: ansi_default;
        color: ansi_default;
        overflow: hidden;
    }

    #source {
        width: 1fr;
        height: 1fr;
        background: ansi_default;
        color: ansi_default;
        overflow: hidden;
        text-wrap: nowrap;
        text-overflow: clip;
    }
    """

    def __init__(self, source_text: str) -> None:
        # Prevent Textual from substituting RGB colors for the terminal palette.
        super().__init__(ansi_color=True)
        self._source_text = source_text

    def compose(self) -> ComposeResult:
        """Give Textual the single widget it should mount and draw."""
        # Markup-looking source such as [bold] must remain literal file content.
        yield Static(self._source_text, id="source", markup=False)
