from mazegen.display.observer import MazeRegenerate, TTYTracker
from mazegen.maze import (
    Maze,
    Pattern,
    make_empty,
    NetworkTracker,
    PacmanTracker,
    make_pacman,
    make_perfect,
)
from mazegen.config.config_parser import Config
from mazegen.maze.output import format_maze
import random

config = Config.parse(open("./example.conf").read())

if config.seed is not None:
    random.seed(config.seed)

maze = Maze(config)

pacman_tracker = PacmanTracker(maze)
network_tracker = NetworkTracker(maze)
tty_tracker = TTYTracker(maze, config) if config.visual else None

excluded = {maze.entry, maze.exit}

pattern = Pattern(config.maze_pattern).centered_for(maze.dims, excluded)


def maze_main() -> None:
    pattern.fill(maze)
    maze.outline()

    walls_const = set(maze.walls_full())

    make_perfect(maze, network_tracker)
    if not config.perfect:
        make_pacman(maze, walls_const, pacman_tracker)

    while config.screensaver:
        make_perfect(maze, network_tracker)
        make_pacman(maze, walls_const, pacman_tracker)


if config.visual:
    while True:
        try:
            if tty_tracker is not None:
                tty_tracker.update = False
                make_empty(maze, set())
                tty_tracker.update = True

            maze_main()

            while tty_tracker is not None:
                tty_tracker.display_maze(wait_for_tick=True)
        except MazeRegenerate:
            continue
else:
    maze_main()
