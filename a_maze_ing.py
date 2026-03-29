from sys import stderr
from typing import Never
from mazegen.config.parser_combinator import ParseError
from mazegen.display.observer import MazeRegenerate, TTYTracker
from mazegen.display.tty import BackendException
from mazegen.maze import (
    Maze,
    Pattern,
    make_empty,
    NetworkTracker,
    PacmanTracker,
    make_pacman,
    make_perfect,
)
from mazegen.config.config_parser import Config, ConfigError
from mazegen.maze.output import format_output
import random

config_filename = "./example.conf"
config_str = open(config_filename).read()


def error(s: str) -> Never:
    print("Error:", file=stderr)
    print(s, end="", file=stderr)
    exit(1)


try:
    config = Config.parse(config_str)
except ParseError as e:
    error(e.pretty_format(config_str, config_filename))
except ConfigError as e:
    error(e.args[0] + "\n")

if config.seed is not None:
    random.seed(config.seed)

maze = Maze(config)

pacman_tracker = PacmanTracker(maze)
network_tracker = NetworkTracker(maze)
try:
    tty_tracker = TTYTracker(maze, config) if config.visual else None
except BackendException as e:
    error(e.args[0] + "\n")

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

            with open(config.output_file, "w") as f:
                f.write(format_output(maze))

            while tty_tracker is not None:
                tty_tracker.display_maze(wait_for_tick=True)
        except MazeRegenerate:
            continue
else:
    maze_main()
