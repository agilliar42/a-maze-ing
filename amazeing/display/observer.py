import time
from amazeing.config.config_parser import Config
from amazeing.display.tty import TTYBackend, TileCycle, TileMaps, extract_pairs
from amazeing.maze.dirty_tracker import DirtyTracker
from amazeing.maze.maze import Maze
from amazeing.maze.path import path_pixels, pathfind_astar
from amazeing.utils.coords import Cardinal


class TTYTracker:
    def __init__(self, maze: Maze, config: Config):
        self.maze = maze
        self.dirty_tracker = DirtyTracker(maze)
        self.backend = TTYBackend(config)
        tilemaps = self.backend.tilemaps
        self.filler_style = TileCycle(tilemaps.filler, self.backend.set_filler)
        self.empty_style = TileCycle(
            tilemaps.empty, self.backend.map_style_cb()
        )
        self.full_style = TileCycle(tilemaps.full, self.backend.map_style_cb())
        self.path_style = TileCycle(tilemaps.path, self.backend.map_style_cb())

        self.backend.set_bg_init(lambda _: self.empty_style.curr_style())

        self.tick: float | None = None
        self.prev_path: list[Cardinal] | None = None
        self.draw_path: bool = True

        maze.observers.add(lambda _: self.display_maze())

    def clear_backend(self) -> None:
        self.backend.set_style(self.empty_style.curr_style())
        for wall in self.dirty_tracker.curr_dirty():
            if self.maze.get_wall(wall):
                continue
            for tile in wall.tile_coords():
                self.backend.draw_tile(tile)

    def path_invalidated(self) -> bool:
        if self.prev_path is None:
            return True
        src = self.maze.entry
        for card in self.prev_path:
            if src.get_wall(card) in self.dirty_tracker.curr_dirty():
                return True
            src = src.get_neighbour(card)
        return False

    def display_path(self) -> None:
        if (
            all(map(self.maze.get_wall, self.dirty_tracker.curr_dirty()))
            and not self.path_invalidated()
            and self.draw_path
        ):
            return None
        path = pathfind_astar(self.maze) if self.draw_path else None
        if self.prev_path is not None:
            self.backend.set_style(self.empty_style.curr_style())
            for tile in path_pixels(self.maze.entry, self.prev_path):
                self.backend.draw_tile(tile)
        self.prev_path = path
        if path is not None:
            self.backend.set_style(self.path_style.curr_style())
            for tile in path_pixels(self.maze.entry, path):
                self.backend.draw_tile(tile)

    def poll_events(self) -> None:
        while True:
            event = self.backend.event()
            if isinstance(event, bool):
                if not event:
                    return
                continue
            if event.sym == "q":
                exit(0)
            if event.sym == "c":
                self.filler_style.cycle()
                self.full_style.cycle()
                self.path_style.cycle()
                self.empty_style.cycle()
            if event.sym == "v":
                self.filler_style.cycle(-1)
                self.full_style.cycle(-1)
                self.path_style.cycle(-1)
                self.empty_style.cycle(-1)
            if event.sym == "p":
                self.draw_path = not self.draw_path
            else:
                continue

    def display_maze(
        self, wait_for_tick: bool = False, frametime: float = 0.016
    ) -> None:
        now = time.monotonic()
        if self.tick is not None:
            if wait_for_tick:
                time.sleep(max(0.0, frametime - now + self.tick))
            elif now - self.tick < frametime:
                return
        self.tick = time.monotonic()

        self.clear_backend()
        self.display_path()

        rewrites = {
            wall
            for wall in self.dirty_tracker.curr_dirty()
            if self.maze.get_wall(wall)
        } | {
            e
            for wall in self.dirty_tracker.curr_dirty()
            for e in wall.neighbours()
            if self.maze.check_coord(e) and self.maze.get_wall(e)
        }

        self.backend.set_style(self.full_style.curr_style())
        for wall in rewrites:
            for pixel in wall.tile_coords():
                self.backend.draw_tile(pixel)
        self.dirty_tracker.clear()
        self.backend.present()
        self.poll_events()
