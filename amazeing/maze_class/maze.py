from typing import Callable, Generator, Iterable, cast

from amazeing.maze_display.backend import IVec2
from .maze_coords import (
    CellCoord,
    Orientation,
    WallCoord,
)

type MazeObserver = Callable[[WallCoord], None]


class Maze:
    def __init__(self, dims: IVec2) -> None:
        self.__dims = dims
        self.observers: set[MazeObserver] = set()
        # list of lines
        self.horizontal: list[list[bool]] = [
            [False for _ in range(0, self.__dims.x)]
            for _ in range(0, self.__dims.y + 1)
        ]
        # list of lines
        self.vertical: list[list[bool]] = [
            [False for _ in range(0, self.__dims.y)]
            for _ in range(0, self.__dims.x + 1)
        ]

    def get_wall(self, coord: WallCoord) -> bool:
        if coord.orientation == Orientation.HORIZONTAL:
            return self.horizontal[coord.a][coord.b]
        return self.vertical[coord.a][coord.b]

    def set_wall(self, coord: WallCoord, value: bool) -> None:
        wall = self.get_wall(coord)
        if wall != value:
            if coord.orientation == Orientation.HORIZONTAL:
                self.horizontal[coord.a][coord.b] = value
            self.vertical[coord.a][coord.b] = value

            for observer in self.observers:
                observer(coord)

    def all_walls(self) -> Generator[WallCoord]:
        for orientation, a_count, b_count in [
            (Orientation.HORIZONTAL, self.__dims.y + 1, self.__dims.x),
            (Orientation.VERTICAL, self.__dims.x + 1, self.__dims.y),
        ]:
            for a in range(0, a_count):
                for b in range(0, b_count):
                    yield WallCoord(orientation, a, b)

    def all_cells(self) -> Iterable[CellCoord]:
        return CellCoord(self.__dims).all_up_to()

    def check_coord(self, coord: WallCoord) -> bool:
        if coord.a < 0 or coord.b < 0:
            return False
        (a_max, b_max) = (
            (self.__dims.y, self.__dims.x - 1)
            if coord.orientation == Orientation.HORIZONTAL
            else (self.__dims.x, self.__dims.y - 1)
        )
        if coord.a > a_max or coord.b > b_max:
            return False
        return True

    def get_walls_checked(self, ids: list[WallCoord]) -> list[bool]:
        return [self.get_wall(id) for id in ids if self.check_coord(id)]

    def get_neighbours(self, id: WallCoord) -> list[bool]:
        return self.get_walls_checked(id.neighbours())

    def outline(self) -> None:
        if self.__dims.x < 1 or self.__dims.y < 1:
            return
        for orientation, a_iter, b_iter in [
            (
                Orientation.VERTICAL,
                (0, self.__dims.x),
                range(0, self.__dims.y),
            ),
            (
                Orientation.HORIZONTAL,
                (0, self.__dims.y),
                range(0, self.__dims.x),
            ),
        ]:
            for a in a_iter:
                for b in b_iter:
                    self.set_wall(WallCoord(orientation, a, b), True)

    def walls_full(self) -> Iterable[WallCoord]:
        return filter(lambda w: self.get_wall(w), self.all_walls())

    def walls_empty(self) -> Iterable[WallCoord]:
        return filter(lambda w: not self.get_wall(w), self.all_walls())
