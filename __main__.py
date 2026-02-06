from amazeing import Maze, TTYBackend, Pattern
import random
from time import sleep

# random.seed(42)

dims = (25, 25)

maze = Maze(dims)

maze.outline()

pattern = Pattern(Pattern.FT_PATTERN).centered_for(dims)
pattern.fill(maze)

walls_const = set(maze.walls_full())


def display_maze(maze: Maze) -> None:
    backend = TTYBackend(*dims, style="\x1b[48;5;240m  \x1b[0m")
    backend.set_style("\x1b[48;5;248m  \x1b[0m")
    for wall in maze.walls_full():
        for pixel in wall.pixel_coords():
            backend.draw_pixel(pixel)
    backend.present()
    sleep(0.05)


empty = list(maze.walls_empty())
random.shuffle(empty)
for wall in empty:
    if maze.wall_bisects(wall):
        continue
    maze.fill_wall(wall)
    # display_maze(maze)

iterations = 0
for _ in range(0, iterations):
    walls = [wall for wall in maze.walls_full() if wall not in walls_const]
    random.shuffle(walls)
    for wall in walls:
        if not maze.wall_cuts_cycle(wall):
            continue
        if maze.wall_leaf_neighbours(wall):
            continue
        maze._remove_wall(wall)
        # display_maze(maze)
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
        # display_maze(maze)
maze._rebuild()
display_maze(maze)
