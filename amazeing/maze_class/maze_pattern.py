from .maze import Maze
from .maze_walls import CellCoord
from typing import Callable


class Pattern:
    FT_PATTERN: list[str] = [
        "#   ###",
        "#     #",
        "### ###",
        "  # #  ",
        "  # ###",
    ]

    def __init__(self, pat: list[str]) -> None:
        self.cells: set[CellCoord] = {
            CellCoord(x, y)
            for y, line in enumerate(pat)
            for x, char in enumerate(line)
            if char != " "
        }

    def offset(self, by: tuple[int, int]) -> "Pattern":
        pattern: Pattern = Pattern([])
        pattern.cells = {cell.offset(by) for cell in self.cells}
        return pattern

    def dims(self) -> tuple[int, int]:
        dim_by: Callable[[Callable[[CellCoord], int]], int] = lambda f: (
            max(map(lambda c: f(c) + 1, self.cells), default=0)
            - min(map(f, self.cells), default=0)
        )
        return (dim_by(CellCoord.x), dim_by(CellCoord.y))

    def normalized(self) -> "Pattern":
        min_by: Callable[[Callable[[CellCoord], int]], int] = lambda f: min(
            map(f, self.cells), default=0
        )
        offset: tuple[int, int] = (-min_by(CellCoord.x), -min_by(CellCoord.y))
        return self.offset(offset)

    def centered_for(self, canvas: tuple[int, int]) -> "Pattern":
        normalized: Pattern = self.normalized()
        dims: tuple[int, int] = normalized.dims()
        offset: tuple[int, int] = (
            (canvas[0] - dims[0]) // 2,
            (canvas[1] - dims[1]) // 2,
        )
        return normalized.offset(offset)

    def fill(self, maze: "Maze") -> None:
        for cell in self.cells:
            for wall in cell.walls():
                maze.fill_wall(wall)
