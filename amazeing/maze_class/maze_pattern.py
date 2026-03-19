from collections.abc import Iterable
from amazeing.maze_display.backend import IVec2
from .maze import Maze
from .maze_coords import CellCoord
from typing import Callable


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
        slots = set(
            map(
                lambda e: CellCoord(e + 1),
                CellCoord(canvas - dims - 1).all_up_to(),
            )
        )
        for excluded in excluding:
            slots -= negative.offset(excluded).__cells
        if len(slots) == 0:
            return Pattern([])
        ideal = (canvas - dims) // 2
        slot = min(
            slots, key=lambda c: int.__add__(*((e := c - ideal) * e).xy())
        )

        return normalized.offset(slot)

    def fill(self, maze: "Maze") -> None:
        for cell in self.__cells:
            for wall in cell.walls():
                maze.set_wall(wall, True)
