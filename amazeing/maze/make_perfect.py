from typing import Callable
from amazeing.maze import Maze
import random

from amazeing.maze import NetworkTracker


def make_perfect(
    maze: Maze,
    tracker: NetworkTracker,
    callback: Callable[[Maze], None] = lambda _: None,
) -> None:
    empty = list(maze.walls_empty())
    random.shuffle(empty)
    for wall in empty:
        if not tracker.wall_bisects(wall):
            maze.set_wall(wall, True)
            callback(maze)
