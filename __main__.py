import curses
import time
from amazeing import (
    Maze,
    TTYBackend,
    Pattern,
    maze_make_pacman,
    maze_make_perfect,
)
from time import sleep
from sys import stderr, stdin

from amazeing.config.config_parser import Config
from amazeing.maze_class.maze_walls import Cardinal, CellCoord
from amazeing.maze_display.TTYdisplay import Tile
from amazeing.maze_display.backend import BackendEvent, CloseRequested, IVec2

# from amazeing.maze_display.layout import example

# example()
# exit(0)

# random.seed(42)

# print(Config.parse(stdin.read()).__dict__)

dims = (15, 15)

maze = Maze(dims)

maze.outline()

pattern = Pattern(Pattern.FT_PATTERN).centered_for(dims)
pattern.fill(maze)

walls_const = set(maze.walls_full())

backend = TTYBackend(IVec2(*dims), IVec2(2, 1), IVec2(2, 1))
curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_BLACK)
black = curses.color_pair(1)
empty = (" ", black)
style_empty = backend.add_style(
    Tile(
        [
            [empty, empty, empty, empty],
            [empty, empty, empty, empty],
        ]
    )
)
curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_WHITE)
white = curses.color_pair(2)
full = (" ", white)
style_full = backend.add_style(
    Tile(
        [
            [full, full, full, full],
            [full, full, full, full],
        ]
    )
)


def clear_backend() -> None:
    dims = backend.dims() * 2 + 1
    backend.set_style(style_empty)
    for x in range(dims.x):
        for y in range(dims.y):
            backend.draw_tile(IVec2(x, y))


def display_maze(maze: Maze) -> None:
    clear_backend()
    backend.set_style(style_full)
    for wall in maze.walls_full():
        for pixel in wall.tile_coords():
            backend.draw_tile(pixel)
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


maze_make_perfect(maze, callback=display_maze)
maze_make_pacman(maze, walls_const, callback=display_maze)
while False:
    maze_make_perfect(maze, callback=display_maze)
    maze_make_pacman(maze, walls_const, callback=display_maze)
    maze._rebuild()
poll_events()
