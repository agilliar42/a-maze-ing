from .maze import Maze
from mazegen.utils import CellCoord, Cardinal
from mazegen.maze.path import pathfind_astar


def to_hex(cell: list[bool]):
    val = (
        1
        if cell[0]
        else (
            0 + 2 if cell[1] else 0 + 4 if cell[2] else 0 + 8 if cell[3] else 0
        )
    )
    return "0123456789ABCDEF"[val]


def format_maze(maze: Maze) -> str:
    dims = maze.dims
    maze_str = ""
    for y in range(dims.y):
        for x in range(dims.x):
            cell = CellCoord(x, y)
            n, e, s, w = map(
                lambda card: maze.get_wall(cell.get_wall(card)),
                [Cardinal.NORTH, Cardinal.EAST, Cardinal.SOUTH, Cardinal.WEST],
            )
            maze_str += to_hex([n, e, s, w])
        maze_str += "\n"
    return maze_str


def format_doors(maze: Maze) -> str:
    entry = f"{maze.entry.x},{maze.entry.y}\n"
    exit = f"{maze.exit.x},{maze.exit.y}\n"
    return entry + exit


def format_path(maze: Maze) -> str:
    path = pathfind_astar(maze)
    return "".join(map(str, path)) + "\n"


def format_output(maze: Maze) -> str:
    return format_maze(maze) + "\n" + format_doors(maze) + format_path(maze)
