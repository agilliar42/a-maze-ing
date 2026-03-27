from mazegen.maze import Maze
from mazegen.utils import WallCoord
import random


def make_empty(
    maze: Maze,
    walls_const: set[WallCoord],
) -> None:
    walls = [wall for wall in maze.walls_full() if wall not in walls_const]
    random.shuffle(walls)
    for wall in walls:
        maze.set_wall(wall, False)
