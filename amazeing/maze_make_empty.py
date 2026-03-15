from collections.abc import Callable
from amazeing.maze_class.maze import Maze
from amazeing.maze_class.maze_coords import WallCoord
import random


def maze_make_empty(
    maze: Maze,
    walls_const: set[WallCoord],
    callback: Callable[[Maze], None] = lambda _: None,
) -> None:
    walls = [wall for wall in maze.walls_full() if wall not in walls_const]
    random.shuffle(walls)
    for wall in walls:
        maze.set_wall(wall)
        callback(maze)
