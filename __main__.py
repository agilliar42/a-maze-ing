import time
from amazeing.maze import (
    Maze,
    Pattern,
)
from amazeing.display import TTYBackend
import random


from amazeing.config.config_parser import Config
from amazeing.maze.path import path_pixels, pathfind_astar
from amazeing.utils import CellCoord
from amazeing.maze import (
    NetworkTracker,
    DirtyTracker,
    PacmanTracker,
    make_pacman,
    make_perfect,
)
from amazeing.display import TileCycle, TileMaps, extract_pairs
from amazeing.utils import IVec2
from amazeing.utils.coords import Cardinal

config = Config.parse(open("./example.conf").read())

if config.seed is not None:
    random.seed(config.seed)

dims = IVec2(config.width, config.height)

maze = Maze(dims)

dirty_tracker = DirtyTracker(maze)
pacman_tracker = PacmanTracker(maze)
network_tracker = NetworkTracker(maze)

backend = TTYBackend(dims, config.tilemap_wall_size, config.tilemap_cell_size)
pair_map = extract_pairs(config)
tilemaps = TileMaps(config, pair_map, backend)
filler_style = TileCycle(tilemaps.filler, backend.set_filler)
empty_style = TileCycle(tilemaps.empty, backend.map_style_cb())
backend.set_bg_init(lambda _: empty_style.curr_style())

full_style = TileCycle(tilemaps.full, backend.map_style_cb())

path_style = TileCycle(tilemaps.path, backend.map_style_cb())


def clear_backend() -> None:
    backend.set_style(empty_style.curr_style())
    for wall in dirty_tracker.curr_dirty():
        if maze.get_wall(wall):
            continue
        for tile in wall.tile_coords():
            backend.draw_tile(tile)


class Tick:
    tick: float | None = None


def display_path() -> None:
    if config.entry is None or config.exit is None:
        return
    path = pathfind_astar(
        maze, network_tracker, CellCoord(config.entry), CellCoord(config.exit)
    )
    if path is not None:
        backend.set_style(path_style.curr_style())
        for tile in path_pixels(CellCoord(config.entry), path):
            backend.draw_tile(tile)


def display_maze(maze: Maze) -> None:
    now = time.monotonic()
    if Tick.tick is not None and now - Tick.tick < 0.016:
        return
    Tick.tick = time.monotonic()

    clear_backend()
    backend.map_style(path_style.curr_style(), empty_style.curr_style())
    display_path()

    rewrites = {
        wall for wall in dirty_tracker.curr_dirty() if maze.get_wall(wall)
    } | {
        e
        for wall in dirty_tracker.curr_dirty()
        for e in wall.neighbours()
        if maze.check_coord(e) and maze.get_wall(e)
    }

    backend.set_style(full_style.curr_style())
    for wall in rewrites:
        for pixel in wall.tile_coords():
            backend.draw_tile(pixel)
    dirty_tracker.clear()
    backend.present()
    poll_events(0)


def poll_events(timeout_ms: int = -1) -> None:
    start = time.monotonic()

    def elapsed_ms() -> int:
        return int((time.monotonic() - start) * 1000.0)

    def timeout() -> int:
        return max(timeout_ms - elapsed_ms(), 0) if timeout_ms != -1 else -1

    backend.present()
    while True:
        event = backend.event(timeout())
        if isinstance(event, bool):
            if timeout() == 0 and not event:
                return
            continue
        if event.sym == "q":
            exit(0)
        if event.sym == "c":
            filler_style.cycle()
            full_style.cycle()
            path_style.cycle()
            empty_style.cycle()
        else:
            continue


excluded = set()
if config.entry is not None:
    excluded.add(CellCoord(config.entry))
if config.exit is not None:
    excluded.add(CellCoord(config.exit))

pattern = Pattern(config.maze_pattern).centered_for(dims, excluded)
pattern.fill(maze)
maze.outline()

walls_const = set(maze.walls_full())

make_perfect(maze, network_tracker, callback=display_maze)
make_pacman(maze, walls_const, pacman_tracker, callback=display_maze)


while False:
    make_perfect(maze, network_tracker, callback=display_maze)
    # poll_events(200)
    make_pacman(maze, walls_const, callback=display_maze)
    # maze_make_empty(maze, walls_const, callback=display_maze)
    # poll_events(200)
    # maze._rebuild()


while True:
    poll_events(16)

backend.uninit()
print(network_tracker.contour_bound((CellCoord(0, 1), Cardinal.EAST)))
