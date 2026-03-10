import time
from amazeing import (
    Maze,
    TTYBackend,
    Pattern,
    maze_make_pacman,
    maze_make_perfect,
    maze_make_empty,
)
import random

from amazeing.config.config_parser import Config
from amazeing.maze_class.maze_walls import Cardinal, CellCoord
from amazeing.maze_display.TTYdisplay import TileCycle, TileMaps, extract_pairs
from amazeing.maze_display.backend import CloseRequested, IVec2

config = Config.parse(open("./example.conf").read())

if config.seed is not None:
    random.seed(config.seed)

dims = IVec2(config.width, config.height)

maze = Maze(dims)

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
    for wall in maze.walls_dirty():
        if maze.get_wall(wall).is_full():
            continue
        for tile in wall.tile_coords():
            backend.draw_tile(tile)


def display_maze(maze: Maze) -> None:
    clear_backend()
    pathfind()
    backend.set_style(full.curr_style())

    rewrites = {
        wall for wall in maze.walls_dirty() if maze.get_wall(wall).is_full()
    } | {
        e
        for wall in maze.walls_dirty()
        for e in wall.neighbours()
        if maze._check_coord(e) and maze.get_wall(e).is_full()
    }

    for wall in rewrites:
        for pixel in wall.tile_coords():
            backend.draw_tile(pixel)
    maze.clear_dirty()
    backend.present()
    poll_events(0)


def poll_events(timeout_ms: int = -1) -> None:
    start = time.monotonic()
    elapsed_ms = lambda: int((time.monotonic() - start) * 1000.0)
    timeout = lambda: (
        max(timeout_ms - elapsed_ms(), 0) if timeout_ms != -1 else -1
    )
    while True:
        event = backend.event(timeout())
        if event is None:
            if timeout_ms == -1:
                continue
            return
        if isinstance(event, CloseRequested) or event.sym == "q":
            exit(0)
        if event.sym == "c":
            filler.cycle()
            full.cycle()
            path.cycle()
            empty.cycle()
        else:
            continue
        backend.present()


prev_path: list[IVec2] = []


def pathfind() -> None:
    if config.entry is None or config.exit is None:
        return
    solution = maze.pathfind(CellCoord(config.entry), CellCoord(config.exit))
    if solution is None:
        return
    tiles = Cardinal.path_to_tiles(solution, CellCoord(config.entry))
    if prev_path == tiles:
        return
    backend.set_style(empty.curr_style())
    for tile in prev_path:
        backend.draw_tile(tile)
    prev_path.clear()
    prev_path.extend(tiles)
    backend.set_style(path.curr_style())
    for tile in tiles:
        backend.draw_tile(tile)
    backend.present()


maze_make_perfect(maze, callback=display_maze)
maze_make_pacman(maze, walls_const, callback=display_maze)


pathfind()


while False:
    maze_make_perfect(maze, callback=display_maze)
    # poll_events(200)
    maze_make_pacman(maze, walls_const, callback=display_maze)
    # maze_make_empty(maze, walls_const, callback=display_maze)
    # poll_events(200)
    maze._rebuild()
poll_events()
