from enum import Enum, auto
from typing import Callable, Generator, Iterable, Optional, cast

from amazeing.display import PixelCoord


class NetworkID:
    __uuid_gen: int = 0

    def __init__(self) -> None:
        self.uuid: int = NetworkID.__uuid_gen
        NetworkID.__uuid_gen += 1


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
            return [CellCoord(self.b, self.a), CellCoord(self.b, self.a - 1)]
        return [CellCoord(self.a, self.b), CellCoord(self.a - 1, self.b)]


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


class WallNetwork:
    def __init__(self) -> None:
        self.walls: set[WallCoord] = set()

    def size(self) -> int:
        return len(self.walls)

    def add_wall(self, id: WallCoord) -> None:
        self.walls.add(id)


class Maze:
    def __init__(self, width: int, height: int) -> None:
        self.width: int = width
        self.height: int = height
        # list of lines
        self.horizontal: list[list[MazeWall]] = [
            [MazeWall() for _ in range(0, width)] for _ in range(0, height + 1)
        ]
        # list of lines
        self.vertical: list[list[MazeWall]] = [
            [MazeWall() for _ in range(0, height)] for _ in range(0, width + 1)
        ]
        self.networks: dict[NetworkID, WallNetwork] = {}

    def _get_wall(self, id: WallCoord) -> MazeWall:
        if id.orientation == Orientation.HORIZONTAL:
            return self.horizontal[id.a][id.b]
        return self.vertical[id.a][id.b]

    def all_walls(self) -> Generator[WallCoord]:
        for orientation, a_count, b_count in [
            (Orientation.HORIZONTAL, self.height + 1, self.width),
            (Orientation.VERTICAL, self.width + 1, self.height),
        ]:
            for a in range(0, a_count):
                for b in range(0, b_count):
                    yield WallCoord(orientation, a, b)

    def _check_id(self, id: WallCoord) -> bool:
        if id.a < 0 or id.b < 0:
            return False
        (a_max, b_max) = (
            (self.height, self.width - 1)
            if id.orientation == Orientation.HORIZONTAL
            else (self.width, self.height - 1)
        )
        if id.a > a_max or id.b > b_max:
            return False
        return True

    def get_walls_checked(self, ids: list[WallCoord]) -> list[MazeWall]:
        return [self._get_wall(id) for id in ids if self._check_id(id)]

    def get_neighbours(self, id: WallCoord) -> list[MazeWall]:
        return self.get_walls_checked(id.neighbours())

    def _fill_wall_alone(self, id: WallCoord, wall: MazeWall) -> None:
        network_id: NetworkID = NetworkID()
        wall.network_id = network_id
        network = WallNetwork()
        network.add_wall(id)
        self.networks[network_id] = network

    def fill_wall(self, id: WallCoord) -> None:
        wall: MazeWall = self._get_wall(id)

        if wall.is_full():
            return

        networks = {
            cast(NetworkID, neighbour.network_id)
            for neighbour in self.get_neighbours(id)
            if neighbour.is_full()
        }

        if len(networks) == 0:
            return self._fill_wall_alone(id, wall)

        dest_id = max(networks, key=lambda n: self.networks[n].size())
        dest = self.networks[dest_id]

        wall.network_id = dest_id
        dest.add_wall(id)

        for to_merge in filter(lambda n: n != dest_id, networks):
            for curr in self.networks[to_merge].walls:
                self._get_wall(curr).network_id = dest_id
                dest.add_wall(curr)

            del self.networks[to_merge]

    def outline(self) -> None:
        if self.width < 1 or self.height < 1:
            return
        for orientation, a_iter, b_iter in [
            (Orientation.VERTICAL, (0, self.width), range(0, self.height)),
            (Orientation.HORIZONTAL, (0, self.height), range(0, self.width)),
        ]:
            for a in a_iter:
                for b in b_iter:
                    self.fill_wall(WallCoord(orientation, a, b))

    def walls_full(self) -> Iterable[WallCoord]:
        return filter(lambda w: self._get_wall(w).is_full(), self.all_walls())

    def walls_empty(self) -> Iterable[WallCoord]:
        return filter(
            lambda w: not self._get_wall(w).is_full(), self.all_walls()
        )

    def wall_bisects(self, wall: WallCoord) -> bool:
        a = {
            cast(NetworkID, neighbour.network_id)
            for neighbour in self.get_walls_checked(wall.a_neighbours())
            if neighbour.is_full()
        }
        b = {
            cast(NetworkID, neighbour.network_id)
            for neighbour in self.get_walls_checked(wall.b_neighbours())
            if neighbour.is_full()
        }
        return len(a & b) != 0

    def wall_cuts_cycle(self, wall: WallCoord) -> bool:
        return any(
            len(
                [
                    ()
                    for wall in self.get_walls_checked(list(cell.walls()))
                    if wall.is_full()
                ]
            )
            >= 2
            for cell in wall.neighbour_cells()
        )
