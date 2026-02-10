__version__ = "0.0.0"
__author__ = "luflores & agilliar"

from amazeing.maze_class import WallCoord, Maze, Pattern
from amazeing.maze_display import Backend, PixelCoord, TTYBackend
from .maze_make_pacman import maze_make_pacman
from .maze_make_perfect import maze_make_perfect

__all__ = [
    "WallCoord",
    "Maze",
    "Pattern",
    "Backend",
    "PixelCoord",
    "TTYBackend",
    "maze_make_pacman",
    "maze_make_perfect",
]
