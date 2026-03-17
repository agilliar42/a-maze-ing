from sys import stderr
from typing import Callable
from amazeing import Maze, WallCoord
import random

from amazeing.maze_class.maze_dirty_tracker import MazeDirtyTracker


def maze_make_pacman(
    maze: Maze,
    walls_const: set[WallCoord],
    dirty_tracker: MazeDirtyTracker,
    callback: Callable[[Maze], None] = lambda _: None,
    iterations: int = 10,
) -> None:
    for _ in range(0, iterations):
        walls = dirty_tracker.clear()
        n = 0
        for wall in walls:
            if not maze.get_wall(wall) or wall in walls_const:
                continue
            leaf_neighbours = maze.wall_leaf_neighbours(wall)
            if not maze.wall_cuts_cycle(wall):
                continue
            if len(leaf_neighbours) == 0:
                maze.set_wall(wall, False)
            else:
                maze.set_wall(wall, False)
                maze.set_wall(random.choice(leaf_neighbours), True)
            n += 1
            callback(maze)
        if n == 0:
            break
