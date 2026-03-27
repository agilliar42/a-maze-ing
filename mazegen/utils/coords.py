from enum import Enum, auto
from typing import Iterable, cast, overload
from mazegen.utils.ivec2 import IVec2


class Orientation(Enum):
    HORIZONTAL = auto()
    VERTICAL = auto()

    def opposite(self) -> "Orientation":
        if self == Orientation.HORIZONTAL:
            return Orientation.VERTICAL
        return Orientation.HORIZONTAL


class Cardinal(Enum):
    NORTH = auto()
    SOUTH = auto()
    EAST = auto()
    WEST = auto()

    def opposite(self) -> "Cardinal":
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
        return self.left().opposite()

    def __repr__(self) -> str:
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
        return [Cardinal.NORTH, Cardinal.SOUTH, Cardinal.EAST, Cardinal.WEST]

    @staticmethod
    def path_to_tiles(path: list["Cardinal"], src: "CellCoord") -> list[IVec2]:
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
        res = [src]
        for card in path:
            src = src.get_neighbour(card)
            res.append(src)
        return res

    @staticmethod
    def path_to_walls(
        path: list["Cardinal"], src: "CellCoord"
    ) -> list["WallCoord"]:
        return [
            cell.get_wall(card)
            for cell, card in zip(Cardinal.path_to_cells(path, src), path)
        ]


class WallCoord:
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
        return [
            WallCoord(self.orientation.opposite(), self.b, self.a - 1),
            WallCoord(self.orientation, self.a, self.b - 1),
            WallCoord(self.orientation.opposite(), self.b, self.a),
        ]

    def b_neighbours(self) -> list["WallCoord"]:
        return [
            WallCoord(self.orientation.opposite(), self.b + 1, self.a - 1),
            WallCoord(self.orientation, self.a, self.b + 1),
            WallCoord(self.orientation.opposite(), self.b + 1, self.a),
        ]

    def neighbours(self) -> list["WallCoord"]:
        return self.a_neighbours() + self.b_neighbours()

    def tile_coords(self) -> Iterable[IVec2]:
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
        def find_cardinal(cell: CellCoord) -> Cardinal:
            for cardinal in Cardinal.all():
                if cell.get_wall(cardinal) == self:
                    return cardinal
            raise Exception("Find cardinal on wall not on cell")

        a, b = self.neighbour_cells()
        return ((a, find_cardinal(a)), (b, find_cardinal(b)))


class CellCoord(IVec2):
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
        return map(self.get_wall, Cardinal.all())

    def get_wall(self, cardinal: Cardinal) -> WallCoord:
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
        return next(
            filter(
                lambda e: e != self, self.get_wall(cardinal).neighbour_cells()
            )
        )

    def tile_coords(self) -> IVec2:
        return IVec2(self.x * 2 + 1, self.y * 2 + 1)

    def offset(self, by: IVec2) -> "CellCoord":
        return CellCoord(self + by)

    def all_up_to(self) -> Iterable["CellCoord"]:
        for x in range(0, self.x):
            for y in range(0, self.y):
                yield CellCoord(x, y)

    def neighbours_unchecked(self) -> Iterable["CellCoord"]:
        return map(self.get_neighbour, Cardinal.all())


type SplitWall = tuple[CellCoord, Cardinal]


def split_wall_cw(wall: SplitWall) -> SplitWall:
    return (wall[0].get_neighbour(wall[1]), wall[1].right())


def split_wall_ccw(wall: SplitWall) -> SplitWall:
    return (wall[0].get_neighbour(wall[1]), wall[1].left())


def split_wall_opposite(wall: SplitWall) -> SplitWall:
    return (wall[0].get_neighbour(wall[1]), wall[1].opposite())
