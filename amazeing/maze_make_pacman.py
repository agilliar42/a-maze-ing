from typing import Any, Callable
from amazeing import Maze, WallCoord
import random


def maze_make_pacman(
    maze: Maze,
    walls_const: set[WallCoord],
    callback: Callable[[Maze], None] = lambda _: None,
    iterations: int = 10,
) -> None:
    for _ in range(0, iterations):
        walls = [wall for wall in maze.walls_full() if wall not in walls_const]
        random.shuffle(walls)
        n = 0
        for wall in walls:
            leaf_neighbours = maze.wall_leaf_neighbours(wall)
            if not maze.wall_cuts_cycle(wall):
                continue
            if len(leaf_neighbours) == 0:
                maze._remove_wall(wall)
            else:
                maze._remove_wall(wall)
                maze.fill_wall(random.choice(leaf_neighbours))
            n += 1
            callback(maze)
        if n == 0:
            break
    maze._rebuild()
