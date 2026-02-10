from amazeing import Maze
import random


def make_perfect(maze: Maze) -> None:
    empty = list(maze.walls_empty())
    random.shuffle(empty)
    for wall in empty:
        if maze.wall_bisects(wall):
            continue
        maze.fill_wall(wall)
