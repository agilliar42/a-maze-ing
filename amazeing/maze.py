from enum import Enum, auto
from typing import Generator, Iterable, Optional, cast

from amazeing.display import PixelCoord


class NetworkID:
    __uuid_gen: int = 0

    def __init__(self) -> None:
        self.uuid = NetworkID.__uuid_gen
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


class WallID:
    def __init__(self, orientation: Orientation, a: int, b: int) -> None:
        self.orientation: Orientation = orientation
        self.a: int = a
        self.b: int = b

    def a_neighbours(self) -> list["WallID"]:
        return [
            WallID(self.orientation.opposite(), self.b, self.a - 1),
            WallID(self.orientation, self.a, self.b - 1),
            WallID(self.orientation.opposite(), self.b, self.a),
        ]

    def b_neighbours(self) -> list["WallID"]:
        return [
            WallID(self.orientation.opposite(), self.b + 1, self.a - 1),
            WallID(self.orientation, self.a, self.b + 1),
            WallID(self.orientation.opposite(), self.b + 1, self.a),
        ]

    def neighbours(self) -> list["WallID"]:
        return self.a_neighbours() + self.b_neighbours()

    def pixel_coords(self) -> Iterable[PixelCoord]:
        a: Iterable[int] = [self.a * 2]
        b: Iterable[int] = [self.b * 2, self.b * 2 + 1, self.b * 2 + 2]
        x_iter: Iterable[int] = a if self.orientation == Orientation.VERTICAL else b
        y_iter: Iterable[int] = a if self.orientation == Orientation.HORIZONTAL else b
        return (PixelCoord(x, y) for x in x_iter for y in y_iter)


class WallNetwork:
    def __init__(self) -> None:
        self.walls: set[WallID] = set()

    def size(self) -> int:
        return len(self.walls)

    def add_wall(self, id: WallID) -> None:
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

    def _get_wall(self, id: WallID) -> MazeWall:
        if id.orientation == Orientation.HORIZONTAL:
            return self.horizontal[id.a][id.b]
        return self.vertical[id.a][id.b]

    def all_walls(self) -> Generator[WallID]:
        for orientation, a_count, b_count in [
            (Orientation.HORIZONTAL, self.height + 1, self.width),
            (Orientation.VERTICAL, self.width + 1, self.height),
        ]:
            for a in range(0, a_count):
                for b in range(0, b_count):
                    yield WallID(orientation, a, b)

    def _check_id(self, id: WallID) -> bool:
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

    def get_walls_checked(self, ids: list[WallID]) -> list[MazeWall]:
        return [self._get_wall(id) for id in ids if self._check_id(id)]

    def get_neighbours(self, id: WallID) -> list[MazeWall]:
        return self.get_walls_checked(id.neighbours())

    def _fill_wall_alone(self, id: WallID, wall: MazeWall) -> None:
        network_id: NetworkID = NetworkID()
        wall.network_id = network_id
        network = WallNetwork()
        network.add_wall(id)
        self.networks[network_id] = network

    def fill_wall(self, id: WallID) -> None:
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
                    self.fill_wall(WallID(orientation, a, b))

    def walls_full(self) -> Iterable[WallID]:
        return filter(lambda w: self._get_wall(w).is_full(), self.all_walls())

    def walls_empty(self) -> Iterable[WallID]:
        return filter(lambda w: not self._get_wall(w).is_full(), self.all_walls())

    def wall_bisects(self, wall: WallID) -> bool:
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
