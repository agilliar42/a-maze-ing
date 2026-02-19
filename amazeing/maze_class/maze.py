from typing import Callable, Generator, Iterable, cast
from .maze_walls import (
    MazeWall,
    NetworkID,
    Orientation,
    WallCoord,
    WallNetwork,
)


class Maze:
    def __init__(self, dims: tuple[int, int]) -> None:
        self.__width: int = dims[0]
        self.__height: int = dims[1]
        self._clear()

    def _clear(self) -> None:
        # list of lines
        self.horizontal: list[list[MazeWall]] = [
            [MazeWall() for _ in range(0, self.__width)]
            for _ in range(0, self.__height + 1)
        ]
        # list of lines
        self.vertical: list[list[MazeWall]] = [
            [MazeWall() for _ in range(0, self.__height)]
            for _ in range(0, self.__width + 1)
        ]
        self.networks: dict[NetworkID, WallNetwork] = {}

    def _rebuild(self) -> None:
        """
        rebuilds the maze to recompute proper connectivity values
        """
        walls = {wall for wall in self.walls_full()}
        self._clear()
        for wall in walls:
            self.fill_wall(wall)

    def get_wall(self, coord: WallCoord) -> MazeWall:
        if coord.orientation == Orientation.HORIZONTAL:
            return self.horizontal[coord.a][coord.b]
        return self.vertical[coord.a][coord.b]

    def _remove_wall(self, coord: WallCoord) -> None:
        """
        removes the wall, without updating network connectivity
        """
        wall = self.get_wall(coord)
        if wall.network_id is not None:
            self.networks[wall.network_id].remove_wall(coord)
            wall.network_id = None

    def all_walls(self) -> Generator[WallCoord]:
        for orientation, a_count, b_count in [
            (Orientation.HORIZONTAL, self.__height + 1, self.__width),
            (Orientation.VERTICAL, self.__width + 1, self.__height),
        ]:
            for a in range(0, a_count):
                for b in range(0, b_count):
                    yield WallCoord(orientation, a, b)

    def _check_coord(self, coord: WallCoord) -> bool:
        if coord.a < 0 or coord.b < 0:
            return False
        (a_max, b_max) = (
            (self.__height, self.__width - 1)
            if coord.orientation == Orientation.HORIZONTAL
            else (self.__width, self.__height - 1)
        )
        if coord.a > a_max or coord.b > b_max:
            return False
        return True

    def get_walls_checked(self, ids: list[WallCoord]) -> list[MazeWall]:
        return [self.get_wall(id) for id in ids if self._check_coord(id)]

    def get_neighbours(self, id: WallCoord) -> list[MazeWall]:
        return self.get_walls_checked(id.neighbours())

    def _fill_wall_alone(self, id: WallCoord, wall: MazeWall) -> None:
        network_id = NetworkID()
        wall.network_id = network_id
        network = WallNetwork()
        network.add_wall(id)
        self.networks[network_id] = network

    def fill_wall(self, id: WallCoord) -> None:
        wall = self.get_wall(id)

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
                self.get_wall(curr).network_id = dest_id
                dest.add_wall(curr)

            del self.networks[to_merge]

    def outline(self) -> None:
        if self.__width < 1 or self.__height < 1:
            return
        for orientation, a_iter, b_iter in [
            (Orientation.VERTICAL, (0, self.__width), range(0, self.__height)),
            (
                Orientation.HORIZONTAL,
                (0, self.__height),
                range(0, self.__width),
            ),
        ]:
            for a in a_iter:
                for b in b_iter:
                    self.fill_wall(WallCoord(orientation, a, b))

    def walls_full(self) -> Iterable[WallCoord]:
        return filter(lambda w: self.get_wall(w).is_full(), self.all_walls())

    def walls_empty(self) -> Iterable[WallCoord]:
        return filter(
            lambda w: not self.get_wall(w).is_full(), self.all_walls()
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
            (
                len(
                    [
                        ()
                        for wall in self.get_walls_checked(list(cell.walls()))
                        if wall.is_full()
                    ]
                )
                >= (3 if self.get_wall(wall).is_full() else 2)
            )
            for cell in wall.neighbour_cells()
        )

    def wall_leaf_neighbours(self, coord: WallCoord) -> list[WallCoord]:
        leaf_f: Callable[
            [Callable[[WallCoord], list[WallCoord]]], list[WallCoord]
        ] = lambda f: (
            list(filter(lambda c: self._check_coord(c), f(coord)))
            if all(
                not wall.is_full() for wall in self.get_walls_checked(f(coord))
            )
            else []
        )
        return leaf_f(WallCoord.a_neighbours) + leaf_f(WallCoord.b_neighbours)
