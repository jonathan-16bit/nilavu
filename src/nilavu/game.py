"""An experimental landscape mode built on the existing terminal viewer."""

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container

from nilavu.app import NilavuApp
from nilavu.lighting import DEFAULT_LIGHT_SETTINGS, LightSettings
from nilavu.palette import DEFAULT_SEED, next_seed, palette_for
from nilavu.world import generate_world
from nilavu.world_view import WorldView


DEFAULT_GAME_LIGHT_SETTINGS = LightSettings(16.0, DEFAULT_LIGHT_SETTINGS.cell_aspect_ratio)


class ForestApp(NilavuApp):
    """Explore one fixed landscape; resizing changes only its viewport."""

    CSS = """
    #frame.game-frame {
        border: none;
        align: center middle;
    }
    #source.game-world {
        max-width: 100%;
        max-height: 100%;
        border: solid ansi_default;
        border-subtitle-color: ansi_default;
        border-subtitle-background: ansi_default;
        border-subtitle-style: none;
        border-subtitle-align: left;
    }
    """

    def __init__(self, source_text: str, *, seed: str = DEFAULT_SEED,
                 theme: str = "forest", light_settings: LightSettings = DEFAULT_GAME_LIGHT_SETTINGS,
                 reveal: bool = False) -> None:
        self._input_text = source_text
        self.world = generate_world(source_text, seed)
        self.reveal = reveal
        super().__init__(self.world.text, seed=seed, theme=theme, light_settings=light_settings)
        self.light_position = self.world.starting_light()

    def compose(self) -> ComposeResult:
        with Container(id="frame", classes="game-frame"):
            yield WorldView(self.world, self.light_position, self.palette,
                            light_settings=self.light_settings, reveal=self.reveal)

    def _apply_palette(self) -> None:
        source = self.query_one(WorldView)
        source.update_palette(self.palette)
        # Extra terminal space is neutral, never lit terrain or walkable ground.
        for widget in (self.screen, source):
            widget.styles.background = "ansi_default"
            widget.styles.color = "ansi_default"
        preview = "reveal | " if self.reveal else ""
        source.border_subtitle = Text(
            f"{preview}{self.world.width}x{self.world.height} {self.palette_theme}"
            f" | seed {ascii(self.seed)} | r world | q quit")

    def action_move_light(self, dx: int, dy: int) -> None:
        position = self.light_position.move(dx, dy)
        if self.world.passable(position.x, position.y):
            super().action_move_light(dx, dy)

    def action_advance_seed(self) -> None:
        # Game seeds describe whole worlds. Regenerate all run state together;
        # ordinary viewer mode retains its existing palette-only behavior.
        self.seed = next_seed(self.seed)
        self.world = generate_world(self._input_text, self.seed)
        self.light_position = self.world.starting_light()
        self.palette = palette_for(self.palette_theme, self.seed)
        self.query_one(WorldView).update_world(self.world, self.light_position)
        self._apply_palette()
