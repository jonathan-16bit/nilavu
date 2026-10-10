"""Display prepared source text inside the current terminal."""

from textual.app import App, ComposeResult
from textual.containers import Container

from nilavu.lighting import DEFAULT_LIGHT_SETTINGS, LightSettings
from nilavu.navigation import LightPosition
from nilavu.palette import DEFAULT_PALETTE
from nilavu.source_view import SourceView


class NilavuApp(App[None], inherit_bindings=False):
    """A full-screen torch viewer for text returned by load_document().

    File loading stays outside the UI: callers validate and prepare the source
    before constructing the app, so a loading error cannot take over the screen.
    """

    # Keep the first screen focused on source text, without framework menus or
    # extra shortcuts. The built-in quit action handles terminal cleanup.
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("h,left", "move_light(-1,0)", "Left"),
        ("j,down", "move_light(0,1)", "Down"),
        ("k,up", "move_light(0,-1)", "Up"),
        ("l,right", "move_light(1,0)", "Right"),
    ]

    # The approved explicit background makes the fade predictable. Colors come
    # from one palette boundary rather than being scattered through rendering.
    # The widget draws a document viewport; framework scrollbars are unnecessary.
    CSS = f"""
    Screen {{
        background: {DEFAULT_PALETTE.color_at(0.0)};
        color: {DEFAULT_PALETTE.color_at(1.0)};
        overflow: hidden;
    }}

    #frame {{
        width: 1fr;
        height: 1fr;
        background: ansi_default;
        border: solid ansi_default;
    }}

    #source {{
        width: 1fr;
        height: 1fr;
        background: {DEFAULT_PALETTE.color_at(0.0)};
        color: {DEFAULT_PALETTE.color_at(1.0)};
        overflow: hidden;
        text-wrap: nowrap;
        text-overflow: clip;
    }}
    """

    def __init__(
        self, source_text: str, *, light_settings: LightSettings = DEFAULT_LIGHT_SETTINGS
    ) -> None:
        # Prevent Textual from substituting RGB colors for the terminal palette.
        super().__init__(ansi_color=True)
        self._source_text = source_text
        self.light_settings = light_settings
        self.light_position = LightPosition.from_text(source_text)

    def compose(self) -> ComposeResult:
        """Mount the source view inside a terminal-colored frame."""
        # A separate frame lets Textual reserve the border's cells. SourceView
        # receives only the interior size, so its coordinates and scroll margins
        # need no special border offsets. ansi_default uses the terminal's own
        # foreground/background pair rather than guessing contrasting RGB values.
        with Container(id="frame"):
            yield SourceView(
                self._source_text, self.light_position, light_settings=self.light_settings
            )

    def action_move_light(self, dx: int, dy: int) -> None:
        """Map an approved movement binding to state, then request a redraw."""
        position = self.light_position.move(dx, dy)
        if position == self.light_position:
            return
        self.light_position = position
        source = self.query_one(SourceView)
        source.update_light(position)
