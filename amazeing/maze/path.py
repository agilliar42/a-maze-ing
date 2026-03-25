from collections.abc import Generator
from dataclasses import dataclass
from amazeing.maze.maze import Maze
from amazeing.maze.network_tracker import NetworkTracker
from amazeing.utils.coords import Cardinal, CellCoord
from amazeing.utils.ivec2 import IVec2
import heapq


def taxicab_distance(a: IVec2, b: IVec2) -> int:
    return sum(a.with_op(lambda lhs, rhs: abs(lhs - rhs), b).xy())


type LinkPath = None | tuple[Cardinal, LinkPath]


@dataclass(slots=True)
class AStarStep:
    dst: CellCoord
    path: LinkPath
    path_length: int
    min_distance: int

    def __lt__(self, other: "AStarStep") -> bool:
        return self.min_distance < other.min_distance or (
            self.min_distance == other.min_distance
            and self.path_length > other.path_length
        )

    def append(self, card: Cardinal, dst: CellCoord) -> "AStarStep":
        next_dst = self.dst.get_neighbour(card)
        next_path = (card, self.path)
        next_dist = self.path_length + 1
        next_min_dist = next_dist + taxicab_distance(next_dst, dst)
        return AStarStep(next_dst, next_path, next_dist, next_min_dist)

    def ends_in_bounds(self, maze: Maze) -> bool:
        return maze.check_cell(self.dst)

    def to_path(self) -> list[Cardinal]:
        curr = self.path
        res = []
        while curr is not None:
            res.append(curr[0])
            curr = curr[1]
        res.reverse()
        return res


def pathfind_astar(
    maze: Maze, network_tracker: NetworkTracker, src: CellCoord, dst: CellCoord
) -> list[Cardinal] | None:
    queue = [AStarStep(src, None, 0, taxicab_distance(src, dst))]
    heapq.heapify(queue)
    visited = set()
    while len(queue) > 0:
        curr = heapq.heappop(queue)
        if curr.dst in visited:
            continue
        if curr.dst == dst:
            return curr.to_path()
        visited.add(curr.dst)
        for card in Cardinal.all():
            if maze.get_wall(curr.dst.get_wall(card)):
                continue
            nxt = curr.append(card, dst)
            if not nxt.ends_in_bounds(maze):
                continue
            heapq.heappush(queue, nxt)
    return None


def path_pixels(curr: CellCoord, path: list[Cardinal]) -> Generator[IVec2]:
    yield curr.tile_coords()
    for card in path:
        nxt = curr.get_neighbour(card)
        yield (curr.tile_coords() + nxt.tile_coords()) // IVec2.splat(2)
        yield nxt.tile_coords()
        curr = nxt
