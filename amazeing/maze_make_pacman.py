from typing import Any, Callable
from amazeing import Maze, WallCoord
import random


def maze_make_pacman(
    maze: Maze,
    walls_const: set[WallCoord],
    callback: Callable[[Maze], None] = lambda _: None,
    iterations: int = 10,
) -> None:
    def walls_full_apply(
        f: Callable[[WallCoord, list[WallCoord]], Any],
        len_pred: Callable[[int], bool],
    ) -> None:
        walls = [wall for wall in maze.walls_full() if wall not in walls_const]
        random.shuffle(walls)
        for wall in walls:
            leaf_neighbours = maze.wall_leaf_neighbours(wall)
            if maze.wall_cuts_cycle(wall) and len_pred(len(leaf_neighbours)):
                f(wall, leaf_neighbours)
                callback(maze)

    def wall_move(wall: WallCoord, leaf_neighbours: list[WallCoord]) -> None:
        maze._remove_wall(wall)
        maze.fill_wall(random.choice(leaf_neighbours))

    for _ in range(0, iterations):
        walls_full_apply(
            lambda wall, _: maze._remove_wall(wall),
            lambda n: n == 0,
        )
        walls_full_apply(
            wall_move,
            lambda n: n != 0,
        )
    maze._rebuild()
