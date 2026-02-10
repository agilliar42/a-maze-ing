from typing import Callable
from amazeing import Maze
import random


def maze_make_perfect(
    maze: Maze, callback: Callable[[Maze], None] = lambda _: None
) -> None:
    empty = list(maze.walls_empty())
    random.shuffle(empty)
    for wall in empty:
        if not maze.wall_bisects(wall):
            maze.fill_wall(wall)
            callback(maze)
