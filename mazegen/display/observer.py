import time
from mazegen.config.config_parser import Config
from mazegen.display.tty import TTYBackend, TileCycle
from mazegen.maze.dirty_tracker import DirtyTracker
from mazegen.maze.maze import Maze
from mazegen.maze.path import pathfind_astar
from mazegen.utils.coords import Cardinal


class MazeRegenerate(Exception):
    pass


class TTYTracker:
    """
    A tracker which may be added to a maze to make it output to tty
    This class probably is doing too much but a refactor sounds more painful

    This manages the different styles for use in interactively cycling them,
    manages the shortest path drawing, pause status, and redrawing only at
    specific intervals
    """

    def __init__(
        self,
        maze: Maze,
        config: Config,
    ):
        self.__maze = maze
        self.__frametime: float = 0.016
        self.__dirty_tracker = DirtyTracker(maze)
        self.__backend = TTYBackend(config)
        tilemaps = self.__backend.tilemaps
        self.__filler_style = TileCycle(
            tilemaps.filler, self.__backend.set_filler
        )
        self.__empty_style = TileCycle(
            tilemaps.empty, self.__backend.map_style_cb()
        )
        self.__full_style = TileCycle(
            tilemaps.full, self.__backend.map_style_cb()
        )
        self.__path_style = TileCycle(
            tilemaps.path, self.__backend.map_style_cb()
        )

        self.__backend.set_bg_init(lambda _: self.__empty_style.curr_style())

        self.__tick: float | None = None
        self.__path: list[Cardinal] | None = None
        self.__draw_path: bool = True

        maze.observers.add(lambda _: self.display_maze())
        self.__paused: bool = False

        self.update: bool = True

    def clear_backend(self) -> None:
        """
        Draws as empty the walls that have been made empty since last redraw
        """
        self.__backend.set_style(self.__empty_style.curr_style())
        for wall in self.__dirty_tracker.curr_dirty():
            if self.__maze.get_wall(wall):
                continue
            for tile in wall.tile_coords():
                self.__backend.draw_tile(tile)

    def path_invalidated(self) -> bool:
        """
        Returns whether the previous path was invalidated since last redraw
        """
        if self.__path is None:
            return True
        src = self.__maze.entry
        for card in self.__path:
            if src.get_wall(card) in self.__dirty_tracker.curr_dirty():
                return True
            src = src.get_neighbour(card)
        return False

    def redraw_path(self, style: int) -> None:
        """
        Draws the current path with the given style
        """
        if self.__path is not None:
            self.__backend.set_style(style)
            for tile in Cardinal.path_to_tiles(self.__path, self.__maze.entry):
                self.__backend.draw_tile(tile)

    def display_path(self) -> None:
        """
        Updates, and redraws if needed, the current path
        """
        if (
            all(map(self.__maze.get_wall, self.__dirty_tracker.curr_dirty()))
            and not self.path_invalidated()
            and self.__draw_path
        ):
            return None
        path = pathfind_astar(self.__maze) if self.__draw_path else None
        self.redraw_path(self.__empty_style.curr_style())
        self.__path = path
        self.redraw_path(self.__path_style.curr_style())

    def poll_events(self) -> None:
        """
        Consumes and processes all the keyboard events
        Raises a MazeRegenerate exception if the user requested it
        """
        while True:
            event = self.__backend.event()
            if isinstance(event, bool):
                if not event:
                    return
                continue
            if event.sym == "q":
                exit(0)
            if event.sym == "c":
                self.__filler_style.cycle()
                self.__full_style.cycle()
                self.__path_style.cycle()
                self.__empty_style.cycle()
            if event.sym == "v":
                self.__filler_style.cycle(-1)
                self.__full_style.cycle(-1)
                self.__path_style.cycle(-1)
                self.__empty_style.cycle(-1)
            if event.sym == "p":
                self.__draw_path = not self.__draw_path
            if event.sym == "k":
                self.__paused = not self.__paused
                try:
                    while self.__paused:
                        self.display_maze(True)
                finally:
                    self.__paused = False
            if event.sym == "r":
                self.redraw_path(self.__empty_style.curr_style())
                self.__path = None
                raise MazeRegenerate
            else:
                continue

    def display_maze(self, wait_for_tick: bool = False) -> None:
        """
        Processes backend events and redraws this backend if the frametime
        was elapsed
        Raises MazeRegenerate exception if the user requested it
        """
        now = time.monotonic()
        if self.__tick is not None:
            if wait_for_tick:
                time.sleep(max(0.0, self.__frametime - now + self.__tick))
            elif now - self.__tick < self.__frametime:
                return
        self.__tick = time.monotonic()

        if not self.update:
            self.__backend.present()
            self.poll_events()
            return

        self.clear_backend()
        self.display_path()

        rewrites = {
            wall
            for wall in self.__dirty_tracker.curr_dirty()
            if self.__maze.get_wall(wall)
        } | {
            e
            for wall in self.__dirty_tracker.curr_dirty()
            for e in wall.neighbours()
            if self.__maze.check_wall(e) and self.__maze.get_wall(e)
        }

        self.__backend.set_style(self.__full_style.curr_style())
        for wall in rewrites:
            for pixel in wall.tile_coords():
                self.__backend.draw_tile(pixel)
        self.__dirty_tracker.clear()
        self.poll_events()
        self.__backend.present()
