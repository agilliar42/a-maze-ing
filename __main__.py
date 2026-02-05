from amazeing import *
import random

maze = Maze(50, 20)
maze.outline()
empty = list(maze.walls_empty())
random.shuffle(empty)
for wall in empty:
    if not maze.wall_bisects(wall):
        maze.fill_wall(wall)

backend = TTYBackend(50, 20)
backend.set_style("#")
for wall in maze.walls_full():
    for pixel in wall.pixel_coords():
        backend.draw_pixel(pixel)
backend.present()
