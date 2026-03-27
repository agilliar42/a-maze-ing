from mazegen.maze import Maze
from mazegen.utils import WallCoord
import random

from mazegen.maze import PacmanTracker


def make_pacman(
    maze: Maze,
    walls_const: set[WallCoord],
    pacman_tracker: PacmanTracker,
    iterations: int = 10,
) -> None:
    for _ in range(0, iterations):
        walls = pacman_tracker.clear()
        n = 0
        while len(walls):
            i = random.randrange(len(walls))
            wall = walls[i]
            del walls[i]
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
        if n == 0:
            break
