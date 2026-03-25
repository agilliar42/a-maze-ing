from typing import Callable, Generator, Iterable
from amazeing.config.config_parser import Config
from amazeing.utils import (
    CellCoord,
    Orientation,
    WallCoord,
    IVec2,
)

type MazeObserver = Callable[[WallCoord], None]


class Maze:
    def __init__(self, config: Config) -> None:
        self.dims = IVec2(config.width, config.height)
        self.observers: set[MazeObserver] = set()
        self.entry: CellCoord = (
            CellCoord(0, 0)
            if config.entry is None
            else CellCoord(config.entry)
        )
        self.exit: CellCoord = (
            CellCoord(self.dims - IVec2.splat(1))
            if config.exit is None
            else CellCoord(config.exit)
        )
        self.__walls_full: dict[WallCoord, None] = {}

    def get_wall(self, coord: WallCoord) -> bool:
        return coord in self.__walls_full

    def set_wall(self, wall: WallCoord, value: bool) -> None:
        if self.get_wall(wall) != value:
            if value:
                self.__walls_full[wall] = None
            else:
                self.__walls_full.pop(wall)

            for observer in self.observers:
                observer(wall)

    def all_walls(self) -> Generator[WallCoord]:
        for orientation, a_count, b_count in [
            (Orientation.HORIZONTAL, self.dims.y + 1, self.dims.x),
            (Orientation.VERTICAL, self.dims.x + 1, self.dims.y),
        ]:
            for a in range(0, a_count):
                for b in range(0, b_count):
                    yield WallCoord(orientation, a, b)

    def all_cells(self) -> Iterable[CellCoord]:
        return CellCoord(self.dims).all_up_to()

    def check_cell(self, cell: CellCoord) -> bool:
        return self.dims.x > cell.x and self.dims.y > cell.y

    def check_coord(self, coord: WallCoord) -> bool:
        if coord.a < 0 or coord.b < 0:
            return False
        (a_max, b_max) = (
            (self.dims.y, self.dims.x - 1)
            if coord.orientation == Orientation.HORIZONTAL
            else (self.dims.x, self.dims.y - 1)
        )
        if coord.a > a_max or coord.b > b_max:
            return False
        return True

    def get_walls_checked(self, ids: list[WallCoord]) -> list[bool]:
        return [self.get_wall(id) for id in ids if self.check_coord(id)]

    def get_neighbours(self, id: WallCoord) -> list[bool]:
        return self.get_walls_checked(id.neighbours())

    def outline(self) -> None:
        if self.dims.x < 1 or self.dims.y < 1:
            return
        for orientation, a_iter, b_iter in [
            (
                Orientation.VERTICAL,
                (0, self.dims.x),
                range(0, self.dims.y),
            ),
            (
                Orientation.HORIZONTAL,
                (0, self.dims.y),
                range(0, self.dims.x),
            ),
        ]:
            for a in a_iter:
                for b in b_iter:
                    self.set_wall(WallCoord(orientation, a, b), True)

    def walls_full(self) -> Iterable[WallCoord]:
        return self.__walls_full

    def walls_empty(self) -> Iterable[WallCoord]:
        return filter(lambda w: not self.get_wall(w), self.all_walls())

    def wall_cuts_cycle(self, wall: WallCoord) -> bool:
        return any(
            (
                len(
                    [
                        ()
                        for wall in self.get_walls_checked(list(cell.walls()))
                        if wall
                    ]
                )
                >= (3 if self.get_wall(wall) else 2)
            )
            for cell in wall.neighbour_cells()
        )

    def wall_leaf_neighbours(self, coord: WallCoord) -> list[WallCoord]:
        leaf_f: Callable[
            [Callable[[WallCoord], list[WallCoord]]], list[WallCoord]
        ] = lambda f: (
            list(filter(lambda c: self.check_coord(c), f(coord)))
            if all(not wall for wall in self.get_walls_checked(f(coord)))
            else []
        )
        return leaf_f(WallCoord.a_neighbours) + leaf_f(WallCoord.b_neighbours)
