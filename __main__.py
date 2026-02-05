from amazeing import Maze, TTYBackend, Pattern
import random


dims = (30, 30)

maze = Maze(*dims)

maze.outline()

pattern = Pattern(Pattern.FT_PATTERN).centered_for(dims)
pattern.fill(maze)

empty = list(maze.walls_empty())
random.shuffle(empty)
for wall in empty:
    if maze.wall_bisects(wall):  # or maze.wall_cuts_cycle(wall):
        continue
    maze.fill_wall(wall)

backend = TTYBackend(*dims, style="\x1b[48;5;240m  \x1b[0m")
backend.set_style("\x1b[48;5;248m  \x1b[0m")
for wall in maze.walls_full():
    for pixel in wall.pixel_coords():
        backend.draw_pixel(pixel)
backend.present()
