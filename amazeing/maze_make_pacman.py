from typing import Callable
from amazeing import Maze, WallCoord
import random

from amazeing.maze_class.maze_pacman_tracker import MazePacmanTracker


def maze_make_pacman(
    maze: Maze,
    walls_const: set[WallCoord],
    pacman_tracker: MazePacmanTracker,
    callback: Callable[[Maze], None] = lambda _: None,
    iterations: int = 10,
) -> None:
    for _ in range(0, iterations):
        walls = pacman_tracker.clear()
        random.shuffle(walls)
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
