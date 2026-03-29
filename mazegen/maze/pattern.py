from collections.abc import Iterable, Generator, Callable
from mazegen.utils import IVec2, CellCoord
from mazegen.maze import Maze


class Pattern:
    """
    A pattern to be filled into the maze
    """

    FT_PATTERN: list[str] = [
        "#   ###",
        "#     #",
        "### ###",
        "  # #  ",
        "  # ###",
    ]

    def __init__(self, pat: list[str] | set[CellCoord]) -> None:
        self.__cells: set[CellCoord]
        if isinstance(pat, set):
            self.__cells = pat
            return
        self.__cells = {
            CellCoord(x, y)
            for y, line in enumerate(pat)
            for x, char in enumerate(line)
            if char != " "
        }

    def offset(self, by: IVec2) -> "Pattern":
        """
        Offsets the pattern by a vector and returns the result
        """
        return Pattern({CellCoord(cell + by) for cell in self.__cells})

    def flood_filled(self) -> "Pattern":
        """
        Fills the pattern to avoid enclosed spaces and returns it
        """
        dims = self.dims()
        border = {CellCoord(-1, -1)}
        reachable = set()
        full = {
            CellCoord(x, y) for x in range(0, dims.x) for y in range(0, dims.y)
        }

        def coord_propagate(coord: CellCoord) -> Iterable[CellCoord]:
            return (
                cell
                for cell in coord.neighbours()
                if cell not in self.__cells
                and cell not in reachable
                and cell not in border
                and cell.x >= -1
                and cell.x <= dims.x
                and cell.y >= -1
                and cell.y <= dims.y
            )

        while len(border) != 0:
            for e in border:
                reachable.add(e)
                border.remove(e)
                for cell in coord_propagate(e):
                    reachable.add(cell)
                    border.add(cell)
                break
        return Pattern(full - reachable)

    def add_cell(self, cell: CellCoord) -> None:
        """
        Adds a cell to the pattern
        """
        self.__cells.add(cell)

    def remove_cell(self, cell: CellCoord) -> None:
        """
        Removes a cell from the pattern
        """
        self.__cells.discard(cell)

    def dims(self) -> IVec2:
        """
        Computes the dims of the pattern
        """
        dim_by: Callable[[Callable[[CellCoord], int]], int] = lambda f: (
            max(map(lambda c: f(c) + 1, self.__cells), default=0)
            - min(map(f, self.__cells), default=0)
        )
        return IVec2(dim_by(lambda e: e.x), dim_by(lambda e: e.y))

    def normalized(self) -> "Pattern":
        """
        Make it so there is at least one cell with a zero coordinate in each
        dimension, and none negative
        """
        min_by: Callable[[Callable[[CellCoord], int]], int] = lambda f: min(
            map(f, self.__cells), default=0
        )
        offset = IVec2(-min_by(lambda e: e.x), -min_by(lambda e: e.y))
        return self.offset(offset)

    def mirrored(self) -> "Pattern":
        """
        Flips the pattern vertically and horizontally
        """
        return Pattern({CellCoord(IVec2.splat(0) - e) for e in self.__cells})

    def centered_for(
        self, canvas: IVec2, excluding: set[CellCoord] = set()
    ) -> "Pattern":
        """
        Centers the pattern for the given canvas without enclosing any coords
        in excluding
        """
        normalized: Pattern = self.normalized()
        negative = normalized.flood_filled().mirrored()
        dims = normalized.dims()

        def middle_range_iter(start: int, end: int) -> Generator[int]:
            r1 = range(end // 2, start - 1, -1)
            r2 = range(end // 2 + 1, end)
            for a, b in zip(r1, r2):
                yield a
                yield b
            for e in r1:
                yield e
            for e in r2:
                yield e

        blacklist = set()
        for excluded in excluding:
            blacklist |= negative.offset(excluded).__cells
        slots = canvas - dims
        for x in middle_range_iter(1, slots.x):
            for y in middle_range_iter(1, slots.y):
                pos = CellCoord(x, y)
                if pos not in blacklist:
                    return normalized.offset(pos)
        return Pattern([])

    def fill(self, maze: "Maze") -> None:
        """
        Fills the pattern into the maze by filling the walls of each pattern
        cell
        """
        for cell in self.__cells:
            for wall in cell.walls():
                maze.set_wall(wall, True)
