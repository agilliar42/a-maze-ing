from collections.abc import Generator
from enum import Enum, auto
from typing import Iterable, cast, overload
from mazegen.utils.ivec2 import IVec2


class Orientation(Enum):
    """
    A simple orientation enum
    """

    HORIZONTAL = auto()
    VERTICAL = auto()

    def opposite(self) -> "Orientation":
        if self == Orientation.HORIZONTAL:
            return Orientation.VERTICAL
        return Orientation.HORIZONTAL


class Cardinal(Enum):
    """
    A cardinal direction
    """

    NORTH = auto()
    SOUTH = auto()
    EAST = auto()
    WEST = auto()

    def opposite(self) -> "Cardinal":
        """
        Gets the cardinal direction opposite of this one
        """
        match self:
            case Cardinal.NORTH:
                return Cardinal.SOUTH
            case Cardinal.SOUTH:
                return Cardinal.NORTH
            case Cardinal.EAST:
                return Cardinal.WEST
            case Cardinal.WEST:
                return Cardinal.EAST

    def left(self) -> "Cardinal":
        """
        Gets the cardinal direction left of this one
        """
        match self:
            case Cardinal.NORTH:
                return Cardinal.WEST
            case Cardinal.SOUTH:
                return Cardinal.EAST
            case Cardinal.EAST:
                return Cardinal.NORTH
            case Cardinal.WEST:
                return Cardinal.SOUTH

    def right(self) -> "Cardinal":
        """
        Gets the cardinal direction right of this one
        """
        return self.left().opposite()

    def __str__(self) -> str:
        match self:
            case Cardinal.NORTH:
                return "N"
            case Cardinal.EAST:
                return "E"
            case Cardinal.SOUTH:
                return "S"
            case Cardinal.WEST:
                return "W"

    @staticmethod
    def all() -> list["Cardinal"]:
        """
        Returns the list of all cardinal directions
        """
        return [Cardinal.NORTH, Cardinal.SOUTH, Cardinal.EAST, Cardinal.WEST]

    @staticmethod
    def path_to_tiles(path: list["Cardinal"], src: "CellCoord") -> list[IVec2]:
        """
        Return the tile coords from a path and start
        """
        res = [src.tile_coords()]
        for card in path:
            nxt = src.get_neighbour(card)
            res.append(
                (src.tile_coords() + nxt.tile_coords()) // IVec2.splat(2)
            )
            res.append(nxt.tile_coords())
            src = nxt
        return res

    @staticmethod
    def path_to_cells(
        path: list["Cardinal"], src: "CellCoord"
    ) -> list["CellCoord"]:
        """
        Return the cell coords from a path and start
        """
        res = [src]
        for card in path:
            src = src.get_neighbour(card)
            res.append(src)
        return res


class WallCoord:
    """
    Wall coordinates
    a is the position in the list of lines/columns, and b is the position in
    said line/column
    """

    def __init__(self, orientation: Orientation, a: int, b: int) -> None:
        self.orientation: Orientation = orientation
        self.a: int = a
        self.b: int = b

    def __members(self) -> tuple[int, int, Orientation]:
        return (self.a, self.b, self.orientation)

    def __eq__(self, value: object, /) -> bool:
        return (
            self.__members() == cast(WallCoord, value).__members()
            if type(self) is type(value)
            else False
        )

    def __hash__(self) -> int:
        return hash(self.__members())

    def a_neighbours(self) -> list["WallCoord"]:
        """
        Returns the neighbours of this wall on an arbitrary a side
        distinct from b_neighbours
        """
        return [
            WallCoord(self.orientation.opposite(), self.b, self.a - 1),
            WallCoord(self.orientation, self.a, self.b - 1),
            WallCoord(self.orientation.opposite(), self.b, self.a),
        ]

    def b_neighbours(self) -> list["WallCoord"]:
        """
        Returns the neighbours of this wall on an arbitrary b side
        distinct from a_neighbours
        """
        return [
            WallCoord(self.orientation.opposite(), self.b + 1, self.a - 1),
            WallCoord(self.orientation, self.a, self.b + 1),
            WallCoord(self.orientation.opposite(), self.b + 1, self.a),
        ]

    def neighbours(self) -> list["WallCoord"]:
        """
        Returns the list of all neigbours for this wall, in arbitrary order
        """
        return self.a_neighbours() + self.b_neighbours()

    def tile_coords(self) -> Iterable[IVec2]:
        """
        Returns the tile coords for this wall
        """
        a: Iterable[int] = [self.a * 2]
        b: Iterable[int] = [self.b * 2, self.b * 2 + 1, self.b * 2 + 2]
        x_iter: Iterable[int] = (
            a if self.orientation == Orientation.VERTICAL else b
        )
        y_iter: Iterable[int] = (
            a if self.orientation == Orientation.HORIZONTAL else b
        )
        return (IVec2(x, y) for x in x_iter for y in y_iter)

    def neighbour_cells(self) -> tuple["CellCoord", "CellCoord"]:
        """
        Returns the cells that are besides this wall
        """
        if self.orientation == Orientation.HORIZONTAL:
            return (
                CellCoord(self.b, self.a),
                CellCoord(self.b, self.a - 1),
            )
        return (
            CellCoord(self.a, self.b),
            CellCoord(self.a - 1, self.b),
        )

    def to_split_wall(
        self,
    ) -> tuple["SplitWall", "SplitWall"]:
        """
        Returns the split wall of each side of this wall
        """

        def find_cardinal(cell: CellCoord) -> Cardinal:
            for cardinal in Cardinal.all():
                if cell.get_wall(cardinal) == self:
                    return cardinal
            raise Exception("Find cardinal on wall not on cell")

        a, b = self.neighbour_cells()
        return ((a, find_cardinal(a)), (b, find_cardinal(b)))


class CellCoord(IVec2):
    """
    A cell coordinate, essentially an IVec2[int] with extra methods
    """

    @overload
    def __init__(self, val: IVec2, /) -> None: ...

    @overload
    def __init__(self, x: int, y: int, /) -> None: ...

    def __init__(self, a: IVec2 | int, b: int = 0) -> None:
        if isinstance(a, int):
            super().__init__(a, b)
        else:
            super().__init__(a.x, a.y)

    def walls(self) -> Iterable[WallCoord]:
        """
        Returns an iterable over the wall of this cell
        """
        return map(self.get_wall, Cardinal.all())

    def get_wall(self, cardinal: Cardinal) -> WallCoord:
        """
        Returns the wall of this cell in the given direction
        """
        match cardinal:
            case Cardinal.NORTH:
                return WallCoord(Orientation.HORIZONTAL, self.y, self.x)
            case Cardinal.SOUTH:
                return WallCoord(Orientation.HORIZONTAL, self.y + 1, self.x)
            case Cardinal.WEST:
                return WallCoord(Orientation.VERTICAL, self.x, self.y)
            case Cardinal.EAST:
                return WallCoord(Orientation.VERTICAL, self.x + 1, self.y)

    def get_neighbour(self, cardinal: Cardinal) -> "CellCoord":
        """
        Returns the cell neighbour of this cell in the given direction
        """
        return next(
            filter(
                lambda e: e != self, self.get_wall(cardinal).neighbour_cells()
            )
        )

    def tile_coords(self) -> IVec2:
        """
        Returns the tile coord of this cell
        """
        return IVec2(self.x * 2 + 1, self.y * 2 + 1)

    def all_up_to(self) -> Generator["CellCoord"]:
        """
        Yields every cell from the origin up to self exclusive
        """
        for x in range(0, self.x):
            for y in range(0, self.y):
                yield CellCoord(x, y)

    def neighbours(self) -> Iterable["CellCoord"]:
        return map(self.get_neighbour, Cardinal.all())


type SplitWall = tuple[CellCoord, Cardinal]


def split_wall_cw(wall: SplitWall) -> SplitWall:
    """
    Rotates a split wall clockwise
    """
    return (wall[0].get_neighbour(wall[1]), wall[1].right())


def split_wall_ccw(wall: SplitWall) -> SplitWall:
    """
    Rotates a split wall counter-clockwise
    """
    return (wall[0].get_neighbour(wall[1]), wall[1].left())


def split_wall_opposite(wall: SplitWall) -> SplitWall:
    """
    Gets the opposite of a split wall
    """
    return (wall[0].get_neighbour(wall[1]), wall[1].opposite())
