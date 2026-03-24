from collections.abc import Callable
from amazeing.maze import Maze
from amazeing.utils import WallCoord
import random


def make_empty(
    maze: Maze,
    walls_const: set[WallCoord],
    callback: Callable[[Maze], None] = lambda _: None,
) -> None:
    walls = [wall for wall in maze.walls_full() if wall not in walls_const]
    random.shuffle(walls)
    for wall in walls:
        maze.set_wall(wall, False)
        callback(maze)
