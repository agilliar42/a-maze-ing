import time
from amazeing import (
    Maze,
    TTYBackend,
    Pattern,
    maze_make_pacman,
    maze_make_perfect,
)
import random


from amazeing.config.config_parser import Config
from amazeing.maze_class.maze_network_tracker import MazeNetworkTracker
from amazeing.maze_class.maze_coords import Cardinal, CellCoord
from amazeing.maze_class.maze_dirty_tracker import MazeDirtyTracker
from amazeing.maze_class.maze_pacman_tracker import MazePacmanTracker
from amazeing.maze_display.TTYdisplay import TileCycle, TileMaps, extract_pairs
from amazeing.maze_display.backend import CloseRequested, IVec2
from amazeing.utils import quadtree

config = Config.parse(open("./example.conf").read())

if config.seed is not None:
    random.seed(config.seed)

dims = IVec2(config.width, config.height)

maze = Maze(dims)

dirty_tracker = MazeDirtyTracker(maze)
pacman_tracker = MazePacmanTracker(maze)

maze.outline()

excluded = set()
if config.entry is not None:
    excluded.add(CellCoord(config.entry))
if config.exit is not None:
    excluded.add(CellCoord(config.exit))

pattern = Pattern(config.maze_pattern).centered_for(dims, excluded)
pattern.fill(maze)

walls_const = set(maze.walls_full())

backend = TTYBackend(dims, config.tilemap_wall_size, config.tilemap_cell_size)
pair_map = extract_pairs(config)
tilemaps = TileMaps(config, pair_map, backend)
filler = TileCycle(tilemaps.filler, backend.set_filler)

empty = TileCycle(tilemaps.empty, backend.map_style_cb())
backend.set_style(empty.curr_style())
for wall in maze.all_walls():
    for tile in wall.tile_coords():
        backend.draw_tile(tile)
for cell in CellCoord(dims).all_up_to():
    backend.draw_tile(cell.tile_coords())

full = TileCycle(tilemaps.full, backend.map_style_cb())

path = TileCycle(tilemaps.path, backend.map_style_cb())


def clear_backend() -> None:
    backend.set_style(empty.curr_style())
    for wall in dirty_tracker.curr_dirty():
        if maze.get_wall(wall):
            continue
        for tile in wall.tile_coords():
            backend.draw_tile(tile)


class Tick:
    tick: float = time.monotonic()


def display_maze(maze: Maze) -> None:
    now = time.monotonic()
    if now - Tick.tick < 0.016:
        return
    Tick.tick = time.monotonic()

    clear_backend()
    # pathfind()
    backend.set_style(full.curr_style())

    rewrites = {
        wall for wall in dirty_tracker.curr_dirty() if maze.get_wall(wall)
    } | {
        e
        for wall in dirty_tracker.curr_dirty()
        for e in wall.neighbours()
        if maze.check_coord(e) and maze.get_wall(e)
    }

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
        if isinstance(event, CloseRequested) or event.sym == "q":
            exit(0)
        if event.sym == "c":
            filler.cycle()
            full.cycle()
            path.cycle()
            empty.cycle()
        else:
            continue


prev_solution: list[Cardinal] = []


def manhattan_distance(a: IVec2, b: IVec2) -> int:
    return sum(map(abs, (a - b).xy()))


def elipse_manhattan(a: IVec2, b: IVec2, a2: IVec2, b2: IVec2) -> int:
    return min(
        manhattan_distance(a1, a2) + manhattan_distance(b1, b2)
        for a1, b1 in ((a, b), (b, a))
    )


# def pathfind_necessary() -> bool:
#    entry = config.entry
#    exit = config.exit
#    if entry is None or exit is None:
#        return False
#    if len(prev_solution) == 0:
#        return True
#    if any(
#        map(
#            lambda e: e in dirty_tracker.curr_dirty() and maze.get_wall(e),
#            Cardinal.path_to_walls(prev_solution, CellCoord(entry)),
#        )
#    ):
#        return True
#    if any(
#        map(
#            lambda e: elipse_manhattan(entry, exit, *e.neighbour_cells())
#            < len(prev_solution),
#            filter(
#                lambda wall: not maze.get_wall(wall),
#                dirty_tracker.curr_dirty(),
#            ),
#        )
#    ):
#        return True
#    return False
#
#
# def pathfind() -> None:
#    if not pathfind_necessary():
#        return
#    if config.entry is None or config.exit is None:
#        return
#    solution = maze.pathfind(CellCoord(config.entry), CellCoord(config.exit))
#    if solution is None or prev_solution == solution:
#        return
#   prev_tiles = Cardinal.path_to_tiles(prev_solution, CellCoord(config.entry))
#    tiles = Cardinal.path_to_tiles(solution, CellCoord(config.entry))
#    backend.set_style(empty.curr_style())
#    for tile in prev_tiles:
#        backend.draw_tile(tile)
#    backend.set_style(path.curr_style())
#    for tile in tiles:
#        backend.draw_tile(tile)
#    backend.present()
#    prev_solution.clear()
#    prev_solution.extend(solution)


network_tracker = MazeNetworkTracker(maze)
maze_make_perfect(maze, network_tracker, callback=display_maze)
maze_make_pacman(maze, walls_const, pacman_tracker, callback=display_maze)


# pathfind()

while False:
    maze_make_perfect(maze, network_tracker, callback=display_maze)
    # poll_events(200)
    maze_make_pacman(maze, walls_const, callback=display_maze)
    # maze_make_empty(maze, walls_const, callback=display_maze)
    # poll_events(200)
    # maze._rebuild()
while True:
    poll_events(16)
