from amazeing import Maze, WallCoord
import random


def maze_make_pacman(maze: Maze, walls_const: set[WallCoord]) -> None:
    iterations = 10
    for _ in range(0, iterations):
        walls = [wall for wall in maze.walls_full() if wall not in walls_const]
        random.shuffle(walls)
        for wall in walls:
            if not maze.wall_cuts_cycle(wall):
                continue
            if maze.wall_leaf_neighbours(wall):
                continue
            maze._remove_wall(wall)
        walls = [wall for wall in maze.walls_full() if wall not in walls_const]
        random.shuffle(walls)
        for wall in walls:
            if not maze.wall_cuts_cycle(wall):
                continue
            leaf_neighbours = maze.wall_leaf_neighbours(wall)
            if len(leaf_neighbours) == 0:
                continue
            maze._remove_wall(wall)
            maze.fill_wall(random.choice(leaf_neighbours))
    maze._rebuild()
