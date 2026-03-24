from collections.abc import Iterable, Generator, Callable
from amazeing.utils import IVec2, CellCoord
from amazeing.maze import Maze


class Pattern:
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
        return Pattern({CellCoord(cell + by) for cell in self.__cells})

    def flood_filled(self) -> "Pattern":
        dims = self.dims()
        border = {CellCoord(-1, -1)}
        reachable = set()
        full = {
            CellCoord(x, y) for x in range(0, dims.x) for y in range(0, dims.y)
        }

        def coord_propagate(coord: CellCoord) -> Iterable[CellCoord]:
            return (
                cell
                for cell in coord.neighbours_unchecked()
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
        self.__cells.add(cell)

    def remove_cell(self, cell: CellCoord) -> None:
        self.__cells.discard(cell)

    def dims(self) -> IVec2:
        dim_by: Callable[[Callable[[CellCoord], int]], int] = lambda f: (
            max(map(lambda c: f(c) + 1, self.__cells), default=0)
            - min(map(f, self.__cells), default=0)
        )
        return IVec2(dim_by(lambda e: e.x), dim_by(lambda e: e.y))

    def normalized(self) -> "Pattern":
        min_by: Callable[[Callable[[CellCoord], int]], int] = lambda f: min(
            map(f, self.__cells), default=0
        )
        offset = IVec2(-min_by(lambda e: e.x), -min_by(lambda e: e.y))
        return self.offset(offset)

    def mirrored(self) -> "Pattern":
        return Pattern({CellCoord(IVec2.splat(0) - e) for e in self.__cells})

    def centered_for(
        self, canvas: IVec2, excluding: set[CellCoord] = set()
    ) -> "Pattern":
        # TODO: don't make a set for the whole maze at the start then
        # remove from it, find the set of invalid spots then iterate
        # through valid spots in order of priority and find the first
        # that matches
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
        for cell in self.__cells:
            for wall in cell.walls():
                maze.set_wall(wall, True)
