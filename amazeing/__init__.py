__version__ = "0.0.0"
__author__ = "luflores & agilliar"

from amazeing.maze_class import WallCoord, Maze, Pattern
from amazeing.maze_display import IVec2, TTYBackend
from .maze_make_pacman import maze_make_pacman
from .maze_make_perfect import maze_make_perfect
from .maze_make_empty import maze_make_empty

__all__ = [
    "WallCoord",
    "Maze",
    "Pattern",
    "IVec2",
    "TTYBackend",
    "maze_make_pacman",
    "maze_make_perfect",
    "maze_make_empty",
]
