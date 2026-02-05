from amazeing import *
import random

maze = Maze(10, 30)
maze.outline()
empty = list(maze.walls_empty())
random.shuffle(empty)
for wall in empty:
    if maze.wall_maintains_topology(wall):
        maze.fill_wall(wall)

backend = TTYBackend(10, 30)
backend.set_style("#")
for wall in maze.walls_full():
    for pixel in wall.pixel_coords():
        backend.draw_pixel(pixel)
backend.present()
