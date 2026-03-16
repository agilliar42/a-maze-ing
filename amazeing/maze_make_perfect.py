from typing import Callable
from amazeing import Maze
import random

from amazeing.maze_class.maze_network_tracker import MazeNetworkTracker


def maze_make_perfect(
    maze: Maze,
    tracker: MazeNetworkTracker,
    callback: Callable[[Maze], None] = lambda _: None,
) -> None:
    empty = list(maze.walls_empty())
    random.shuffle(empty)
    for wall in empty:
        if not tracker.wall_bisects(wall):
            maze.set_wall(wall, True)
            callback(maze)
