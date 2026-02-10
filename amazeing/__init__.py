__version__ = "0.0.0"
__author__ = "luflores & agilliar"

from amazeing.maze_class import WallCoord, Maze, Pattern
from amazeing.maze_display import Backend, PixelCoord, TTYBackend
from .perfect_to_imperfect import perfect_to_imperfect
from .prototype_perfect import make_perfect

__all__ = [
    "WallCoord",
    "Maze",
    "Pattern",
    "Backend",
    "PixelCoord",
    "TTYBackend",
    "perfect_to_imperfect",
    "make_perfect"
]
