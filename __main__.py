from amazeing.display.observer import TTYTracker
from amazeing.maze import (
    Maze,
    Pattern,
    make_empty,
    NetworkTracker,
    PacmanTracker,
    make_pacman,
    make_perfect,
)
from amazeing.config.config_parser import Config
import random

config = Config.parse(open("./example.conf").read())

if config.seed is not None:
    random.seed(config.seed)

maze = Maze(config)

pacman_tracker = PacmanTracker(maze)
network_tracker = NetworkTracker(maze)
tty_tracker = TTYTracker(maze, config)

excluded = {maze.entry, maze.exit}

pattern = Pattern(config.maze_pattern).centered_for(maze.dims, excluded)
pattern.fill(maze)
maze.outline()

walls_const = set(maze.walls_full())

make_perfect(maze, network_tracker)
make_pacman(maze, walls_const, pacman_tracker)


while True:
    make_perfect(maze, network_tracker)
    make_pacman(maze, walls_const, pacman_tracker)
    make_empty(maze, walls_const)


while True:
    tty_tracker.display_maze()

tty_tracker.backend.uninit()
