"""An experimental landscape mode built on the existing terminal viewer."""

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container

from nilavu.app import NilavuApp
from nilavu.companions import Companions
from nilavu.fireflies import new_run
from nilavu.lighting import DEFAULT_LIGHT_SETTINGS, LightSettings
from nilavu.palette import DEFAULT_SEED, next_seed, palette_for
from nilavu.world import generate_world
from nilavu.world_view import WorldView


DEFAULT_GAME_LIGHT_SETTINGS = LightSettings(16.0, DEFAULT_LIGHT_SETTINGS.cell_aspect_ratio)


class ForestApp(NilavuApp):
    """Explore one fixed landscape; resizing changes only its viewport."""

    BINDINGS = [("space", "wake_firefly", "Wake firefly")]

    CSS = """
    #frame.game-frame {
        border: none;
        align: center middle;
    }
    #source.game-world {
        max-width: 100%;
        max-height: 100%;
        border: solid ansi_default;
        border-title-color: ansi_default;
        border-title-background: ansi_default;
        border-title-style: none;
        border-title-align: left;
        border-subtitle-color: ansi_default;
        border-subtitle-background: ansi_default;
        border-subtitle-style: none;
        border-subtitle-align: left;
    }
    """

    def __init__(self, *, seed: str = DEFAULT_SEED,
                 theme: str = "forest", light_settings: LightSettings = DEFAULT_GAME_LIGHT_SETTINGS,
                 reveal: bool = False) -> None:
        self.world = generate_world(seed)
        self.firefly_run = new_run(self.world, seed)
        self.companions = Companions((self.world.spawn,))
        self.reveal = reveal
        super().__init__(self.world.text, seed=seed, theme=theme, light_settings=light_settings)
        self.light_position = self.world.starting_light()

    def compose(self) -> ComposeResult:
        with Container(id="frame", classes="game-frame"):
            yield WorldView(self.world, self.light_position, self.palette,
                            light_settings=self.light_settings, reveal=self.reveal,
                            fireflies=self.firefly_run.fireflies)

    def _apply_palette(self) -> None:
        source = self.query_one(WorldView)
        source.update_palette(self.palette)
        # Extra terminal space is neutral, never lit terrain or walkable ground.
        for widget in (self.screen, source):
            widget.styles.background = "ansi_default"
            widget.styles.color = "ansi_default"
        self._update_status()

    def _update_status(self) -> None:
        source = self.query_one(WorldView)
        nearby = self.firefly_run.nearest_sleeping((self.light_position.x, self.light_position.y),
                                          self.light_settings.cell_aspect_ratio)
        prompt = "Space: wake" if nearby is not None else "find fireflies"
        if self.firefly_run.awake_count == len(self.firefly_run.fireflies):
            prompt = "all awake"
        # Put objective and contextual help first so small terminals retain them.
        source.border_title = Text(f"{self.firefly_run.awake_count}/{len(self.firefly_run.fireflies)} awake | {prompt}")
        preview = "reveal | " if self.reveal else ""
        source.border_subtitle = Text(
            f"{preview}{self.world.width}x{self.world.height} {self.palette_theme}"
            f" | seed {ascii(self.seed)} | r world | q quit")

    def action_move_light(self, dx: int, dy: int) -> None:
        position = self.light_position.move(dx, dy)
        if position != self.light_position and self.world.passable(position.x, position.y):
            super().action_move_light(dx, dy)
            self.companions = self.companions.follow(
                self.world, (position.x, position.y), self.light_settings.cell_aspect_ratio)
            self.query_one(WorldView).update_companions(self.companions.positions)
        self._update_status()

    def action_wake_firefly(self) -> None:
        run = self.firefly_run.wake_nearby((self.light_position.x, self.light_position.y),
                                  self.light_settings.cell_aspect_ratio)
        if run is not self.firefly_run:
            awakened = next(new.position for old, new in zip(self.firefly_run.fireflies, run.fireflies)
                            if new.awake and not old.awake)
            self.firefly_run = run
            # Anchor the new companion to this interaction location so it cannot
            # gather around an older cursor position retained in the trail.
            if self.companions.trail[0] != (self.light_position.x, self.light_position.y):
                self.companions = self.companions.follow(
                    self.world, (self.light_position.x, self.light_position.y),
                    self.light_settings.cell_aspect_ratio)
            self.companions = self.companions.add(
                self.world, awakened, self.light_settings.cell_aspect_ratio)
            self.query_one(WorldView).update_fireflies(run.fireflies)
            self.query_one(WorldView).update_companions(self.companions.positions)
        self._update_status()

    def action_advance_seed(self) -> None:
        # Game seeds describe whole worlds. Regenerate all run state together;
        # ordinary viewer mode retains its existing palette-only behavior.
        self.seed = next_seed(self.seed)
        self.world = generate_world(self.seed)
        self.firefly_run = new_run(self.world, self.seed)
        self.companions = Companions((self.world.spawn,))
        self.light_position = self.world.starting_light()
        self.palette = palette_for(self.palette_theme, self.seed)
        self.query_one(WorldView).update_world(self.world, self.light_position)
        self.query_one(WorldView).update_fireflies(self.firefly_run.fireflies)
        self._apply_palette()
