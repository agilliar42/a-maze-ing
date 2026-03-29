from typing import Callable, Generator, Iterable
from mazegen.config.config_parser import Config
from mazegen.utils import (
    CellCoord,
    Orientation,
    WallCoord,
    IVec2,
)

type MazeObserver = Callable[[WallCoord], None]


class Maze:
    """
    A simple maze class, which is simply a set of filled walls
    Its observers are called whenever the status of a wall changes
    """

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
        """
        Returns whether said wall is filled in
        """
        return coord in self.__walls_full

    def set_wall(self, wall: WallCoord, value: bool) -> None:
        """
        Sets the status of the wall, as in whether it is filled, and
        calls observers if needed
        """
        if self.get_wall(wall) != value:
            if value:
                self.__walls_full[wall] = None
            else:
                self.__walls_full.pop(wall)

            for observer in self.observers:
                observer(wall)

    def all_walls(self) -> Generator[WallCoord]:
        """
        Returns an iterator over all the wall coords that are contained
        within this maze, full or not
        """
        for orientation, a_count, b_count in [
            (Orientation.HORIZONTAL, self.dims.y + 1, self.dims.x),
            (Orientation.VERTICAL, self.dims.x + 1, self.dims.y),
        ]:
            for a in range(0, a_count):
                for b in range(0, b_count):
                    yield WallCoord(orientation, a, b)

    def all_cells(self) -> Iterable[CellCoord]:
        """
        Returns an iterator over all the cell coords of this maze
        """
        return CellCoord(self.dims).all_up_to()

    def check_cell(self, cell: CellCoord) -> bool:
        """
        Returns whether the given cell coord is valid in this maze
        """
        return (
            self.dims.x > cell.x
            and self.dims.y > cell.y
            and cell.x >= 0
            and cell.y >= 0
        )

    def check_wall(self, coord: WallCoord) -> bool:
        """
        Returns whether the given wall coord is valid in this maze
        """
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

    def get_walls_checked(self, walls: list[WallCoord]) -> list[bool]:
        """
        Maps the given wall to whether it is full, skipping out of bound walls
        """
        return [self.get_wall(id) for id in walls if self.check_wall(id)]

    def outline(self) -> None:
        """
        Fills in the outline of the maze, calling observers as needed
        """
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
        """
        Returns an iterator over this maze's filled walls
        The iterator is only valid as long as the walls of the maze don't
        change
        """
        return self.__walls_full

    def walls_empty(self) -> Iterable[WallCoord]:
        """
        Returns an iterator over this maze's empty walls
        The iterator is still valid after a wall has been altered, if it
        was filled it shall not be yielded
        """
        return filter(lambda w: not self.get_wall(w), self.all_walls())

    def wall_causes_impass(self, wall: WallCoord) -> bool:
        """
        Return whether the wall, if full, creates an impass, that is a cell
        with at most 1 empty wall
        """
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

    def wall_leaf_neighbours(self, wall: WallCoord) -> list[WallCoord]:
        """
        From each junction between this wall and other walls, gets either an
        empty list if at least one of them is full, otherwise the list of said
        neighbour walls.
        Returns the result of that operation concatenated for both junctions
        """
        leaf_f: Callable[
            [Callable[[WallCoord], list[WallCoord]]], list[WallCoord]
        ] = lambda f: (
            list(filter(lambda c: self.check_wall(c), f(wall)))
            if all(not wall for wall in self.get_walls_checked(f(wall)))
            else []
        )
        return leaf_f(WallCoord.a_neighbours) + leaf_f(WallCoord.b_neighbours)
