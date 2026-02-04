from enum import Enum
from typing import Optional, cast


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
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"

    def opposite(self) -> "Orientation":
        if self == Orientation.HORIZONTAL:
            return Orientation.VERTICAL
        return Orientation.HORIZONTAL


class WallId:
    def __init__(self, orientation: Orientation, a: int, b: int) -> None:
        self.orientation: Orientation = orientation
        self.a: int = a
        self.b: int = b

    def a_neighbours(self) -> list["WallId"]:
        return [
            WallId(self.orientation.opposite(), self.b - 1, self.a),
            WallId(self.orientation, self.a - 1, self.b),
            WallId(self.orientation.opposite(), self.b, self.a),
        ]

    def b_neighbours(self) -> list["WallId"]:
        return [
            WallId(self.orientation.opposite(), self.b - 1, self.a + 1),
            WallId(self.orientation, self.a + 1, self.b),
            WallId(self.orientation.opposite(), self.b, self.a + 1),
        ]

    def neighbours(self) -> list["WallId"]:
        return self.a_neighbours() + self.b_neighbours()


class WallNetwork:
    def __init__(self) -> None:
        self.walls: set[WallId] = set()

    def size(self) -> int:
        return len(self.walls)

    def add_wall(self, id: WallId) -> None:
        self.walls.add(id)


class Maze:
    def __init__(self, width: int, height: int) -> None:
        self.width: int = width
        self.height: int = height
        self.horizontal: list[list[MazeWall]] = [
            [MazeWall() for _ in range(0, width)] for _ in range(0, height + 1)
        ]
        self.vertical: list[list[MazeWall]] = [
            [MazeWall() for _ in range(0, height)] for _ in range(0, width + 1)
        ]
        self.networks: dict[NetworkID, WallNetwork] = {}

    def _get_wall(self, id: WallId) -> MazeWall:
        if id.orientation == Orientation.HORIZONTAL:
            return self.horizontal[id.a][id.b]
        return self.vertical[id.a][id.b]

    def _check_id(self, id: WallId) -> bool:
        if id.a < 0 or id.b < 0:
            return False
        (a_max, b_max) = (
            (self.height + 1, self.width)
            if id.orientation == Orientation.HORIZONTAL
            else (self.width + 1, self.height)
        )
        if id.a > a_max or id.b > b_max:
            return False
        return True

    def get_walls_checked(self, ids: list[WallId]) -> list[MazeWall]:
        return [self._get_wall(id) for id in ids if self._check_id(id)]

    def get_neighbours(self, id: WallId) -> list[MazeWall]:
        return self.get_walls_checked(id.neighbours())

    def _fill_wall_alone(self, id: WallId, wall: MazeWall) -> None:
        network_id: NetworkID = NetworkID()
        wall.network_id = network_id
        network = WallNetwork()
        network.add_wall(id)
        self.networks[network_id] = network

    def fill_wall(self, id: WallId) -> None:
        wall: MazeWall = self._get_wall(id)

        if wall.is_full():
            return

        networks = {
            cast(NetworkID, neighbour.network_id)
            for neighbour in self.get_neighbours(id)
            if neighbour.is_full()
        }

        if networks == {}:
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
