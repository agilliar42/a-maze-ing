from amazeing import (Maze, TTYBackend, Pattern,
                      perfect_to_imperfect, make_perfect)
from time import sleep

# random.seed(42)

dims = (10, 10)

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


make_perfect(maze)
display_maze(maze)
perfect_to_imperfect(maze, walls_const)
maze._rebuild()
display_maze(maze)
