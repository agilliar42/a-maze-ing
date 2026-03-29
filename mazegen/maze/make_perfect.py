from mazegen.maze import Maze
import random

from mazegen.maze import NetworkTracker


def make_perfect(
    maze: Maze,
    tracker: NetworkTracker,
) -> None:
    """
    Incrementally fills every wall of the maze that doesn't cause it to be
    bisected
    """
    empty = list(maze.walls_empty())
    random.shuffle(empty)
    for wall in empty:
        if not tracker.wall_bisects(wall):
            maze.set_wall(wall, True)
