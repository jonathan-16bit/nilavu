"""Display prepared source text inside the current terminal."""

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Container

from nilavu.lighting import DEFAULT_LIGHT_SETTINGS, LightSettings
from nilavu.navigation import LightPosition
from nilavu.palette import DEFAULT_SEED, DEFAULT_THEME, THEMES, next_seed, palette_for
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
        ("h,a,left", "move_light(-1,0)", "Left"),
        ("j,s,down", "move_light(0,1)", "Down"),
        ("k,w,up", "move_light(0,-1)", "Up"),
        ("l,d,right", "move_light(1,0)", "Right"),
        ("t", "cycle_theme", "Theme"),
        ("r", "advance_seed", "Next forest seed"),
    ]

    # Palette colors are applied on mount, once the selected screen/view exist.
    # The widget draws a document viewport; framework scrollbars are unnecessary.
    CSS = """
    Screen {
        overflow: hidden;
    }

    #frame {
        width: 1fr;
        height: 1fr;
        background: ansi_default;
        border: solid ansi_default;
        border-subtitle-color: ansi_default;
        border-subtitle-background: ansi_default;
        border-subtitle-style: none;
        border-subtitle-align: left;
    }

    #source {
        width: 1fr;
        height: 1fr;
        overflow: hidden;
        text-wrap: nowrap;
        text-overflow: clip;
    }
    """

    def __init__(
        self,
        source_text: str,
        *,
        light_settings: LightSettings = DEFAULT_LIGHT_SETTINGS,
        theme: str = DEFAULT_THEME,
        seed: str = DEFAULT_SEED,
    ) -> None:
        # Prevent Textual from substituting RGB colors for the terminal palette.
        super().__init__(ansi_color=True)
        self._source_text = source_text
        self.light_settings = light_settings
        self.palette_theme = theme
        self.seed = seed
        self.palette = palette_for(theme, seed)
        self.light_position = LightPosition.from_text(source_text)

    async def _ready(self) -> None:
        """Skip Textual's environment-triggered screenshot-and-exit timer."""
        # This Textual 8 hook otherwise saves source text when TEXTUAL_SCREENSHOT
        # is inherited from the shell. Nilavu starts only its interactive viewer.

    def _handle_exception(self, error: Exception) -> None:
        """Exit with a concise diagnostic that cannot include document contents."""
        # Preserve Textual 8's failure status and test-runner propagation, while
        # avoiding exception messages, local variables, and custom Rich output.
        self._return_code = 1
        if self._exception is None:
            self._exception = error
            self._exception_event.set()
        error_type = ascii(type(error).__name__)
        self.panic(Text(f"nilavu: unexpected display error ({error_type})."))

    def compose(self) -> ComposeResult:
        """Mount the source view inside a terminal-colored frame."""
        # A separate frame lets Textual reserve the border's cells. SourceView
        # receives only the interior size, so its coordinates and scroll margins
        # need no special border offsets. ansi_default uses the terminal's own
        # foreground/background pair rather than guessing contrasting RGB values.
        with Container(id="frame"):
            yield SourceView(
                self._source_text,
                self.light_position,
                self.palette,
                light_settings=self.light_settings,
            )

    def on_mount(self) -> None:
        """Use the chosen palette for styled cells and uncovered screen areas."""
        self._apply_palette()

    def _apply_palette(self) -> None:
        """Update colors and status without rebuilding or moving the document."""
        source = self.query_one(SourceView)
        source.palette = self.palette
        source.refresh()
        # Applying both backgrounds keeps dim text and padding at the same dark
        # color. The frame keeps the terminal-default foreground/background pair.
        for widget in (self.screen, source):
            widget.styles.background = self.palette.color_at(0.0)
            widget.styles.color = self.palette.color_at(1.0)
        # A border subtitle uses no source rows. Escape arbitrary seed characters
        # and pass literal Text, so controls and markup cannot affect the terminal.
        status = self.palette_theme
        if self.palette_theme == "forest":
            status += f" | seed {ascii(self.seed)}"
        status += " | t theme | r forest seed | q quit"
        self.query_one("#frame", Container).border_subtitle = Text(status)

    def action_cycle_theme(self) -> None:
        """Switch themes while retaining the latest forest seed."""
        self.palette_theme = THEMES[(THEMES.index(self.palette_theme) + 1) % len(THEMES)]
        self.palette = palette_for(self.palette_theme, self.seed)
        self._apply_palette()

    def action_advance_seed(self) -> None:
        """Generate the next forest palette from the current seed string."""
        if self.palette_theme != "forest":
            return
        self.seed = next_seed(self.seed)
        self.palette = palette_for(self.palette_theme, self.seed)
        self._apply_palette()

    def action_move_light(self, dx: int, dy: int) -> None:
        """Map an approved movement binding to state, then request a redraw."""
        position = self.light_position.move(dx, dy)
        if position == self.light_position:
            return
        self.light_position = position
        source = self.query_one(SourceView)
        source.update_light(position)
