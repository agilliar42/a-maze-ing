from enum import Enum, auto
from typing import Iterable, Optional, cast
from ..maze_display import PixelCoord


class NetworkID:
    __uuid_gen: int = 0

    def __init__(self) -> None:
        self.uuid: int = NetworkID.__uuid_gen
        NetworkID.__uuid_gen += 1


class WallNetwork:
    def __init__(self) -> None:
        from .maze_walls import WallCoord
        self.walls: set[WallCoord] = set()

    def size(self) -> int:
        return len(self.walls)

    def add_wall(self, id: "WallCoord") -> None:
        self.walls.add(id)

    def remove_wall(self, id: "WallCoord") -> None:
        self.walls.remove(id)


class MazeWall:
    def __init__(self, network_id: Optional[NetworkID] = None) -> None:
        self.network_id: Optional[NetworkID] = network_id

    def is_full(self) -> bool:
        return self.network_id is not None


class Orientation(Enum):
    HORIZONTAL = auto()
    VERTICAL = auto()

    def opposite(self) -> "Orientation":
        if self == Orientation.HORIZONTAL:
            return Orientation.VERTICAL
        return Orientation.HORIZONTAL


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

    def pixel_coords(self) -> Iterable[PixelCoord]:
        a: Iterable[int] = [self.a * 2]
        b: Iterable[int] = [self.b * 2, self.b * 2 + 1, self.b * 2 + 2]
        x_iter: Iterable[int] = (
            a if self.orientation == Orientation.VERTICAL else b
        )
        y_iter: Iterable[int] = (
            a if self.orientation == Orientation.HORIZONTAL else b
        )
        return (PixelCoord(x, y) for x in x_iter for y in y_iter)

    def neighbour_cells(self) -> list["CellCoord"]:
        if self.orientation == Orientation.HORIZONTAL:
            return [
                CellCoord(self.b, self.a),
                CellCoord(self.b, self.a - 1),
            ]
        return [
            CellCoord(self.a, self.b),
            CellCoord(self.a - 1, self.b),
        ]


class CellCoord:
    def __init__(self, x: int, y: int) -> None:
        self.__x: int = x
        self.__y: int = y

    def __members(self) -> tuple[int, int]:
        return (self.__x, self.__y)

    def __eq__(self, value: object, /) -> bool:
        return (
            self.__members() == cast(CellCoord, value).__members()
            if type(self) is type(value)
            else False
        )

    def __hash__(self) -> int:
        return hash(self.__members())

    def walls(self) -> Iterable[WallCoord]:
        return [
            WallCoord(Orientation.HORIZONTAL, self.__y, self.__x),
            WallCoord(Orientation.HORIZONTAL, self.__y + 1, self.__x),
            WallCoord(Orientation.VERTICAL, self.__x, self.__y),
            WallCoord(Orientation.VERTICAL, self.__x + 1, self.__y),
        ]

    def pixel_coords(self) -> Iterable[PixelCoord]:
        return [PixelCoord(self.__x * 2 + 1, self.__y * 2 + 1)]

    def offset(self, by: tuple[int, int]) -> "CellCoord":
        return CellCoord(self.__x + by[0], self.__y + by[1])

    def x(self) -> int:
        return self.__x

    def y(self) -> int:
        return self.__y
