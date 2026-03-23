__version__ = "0.0.0"
__author__ = "luflores & agilliar"


from .maze.maze_coords import WallCoord
from .maze.maze import Maze
from .maze.maze_pattern import Pattern
from .maze_display.TTYdisplay import TTYBackend
from .maze_make_empty import maze_make_empty
from .maze_make_perfect import maze_make_perfect
from .maze_make_pacman import maze_make_pacman

__all__ = [
    "Maze",
    "WallCoord",
    "TTYBackend",
    "Pattern",
    "maze_make_empty",
    "maze_make_perfect",
    "maze_make_pacman",
]
