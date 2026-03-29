from dataclasses import dataclass
from mazegen.maze.maze import Maze
from mazegen.utils.coords import Cardinal, CellCoord
from mazegen.utils.ivec2 import IVec2
import heapq


def taxicab_distance(a: IVec2, b: IVec2) -> int:
    """
    Returns the taxicab/manhattan distance between two points
    """
    return sum(a.with_op(lambda lhs, rhs: abs(lhs - rhs), b).xy())


type LinkPath = None | tuple[Cardinal, LinkPath]


@dataclass(slots=True)
class AStarStep:
    """
    A step in A* pathfinding, containing the previously traversed path as
    well as distance heuristics for the grid
    """

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
        """
        Adds the current direction to the path and returns it, with target
        coord dst
        """
        next_dst = self.dst.get_neighbour(card)
        next_path = (card, self.path)
        next_dist = self.path_length + 1
        next_min_dist = next_dist + taxicab_distance(next_dst, dst)
        return AStarStep(next_dst, next_path, next_dist, next_min_dist)

    def ends_in_bounds(self, maze: Maze) -> bool:
        """
        Checks whether this step ends within the maze
        """
        return maze.check_cell(self.dst)

    def to_path(self) -> list[Cardinal]:
        """
        Turns this step to a path as a list of cardinal directions
        """
        curr = self.path
        res = []
        while curr is not None:
            res.append(curr[0])
            curr = curr[1]
        res.reverse()
        return res


def pathfind_astar(maze: Maze) -> list[Cardinal] | None:
    """
    Finds the shortest path between the entrance and exit using A*
    """
    src = maze.entry
    dst = maze.exit
    queue = [AStarStep(src, None, 0, taxicab_distance(src, dst))]
    heapq.heapify(queue)
    visited = {src}
    while len(queue) > 0:
        curr = heapq.heappop(queue)
        if curr.dst == dst:
            return curr.to_path()
        for card in Cardinal.all():
            if maze.get_wall(curr.dst.get_wall(card)):
                continue
            nxt = curr.append(card, dst)
            if nxt.dst in visited or not nxt.ends_in_bounds(maze):
                continue
            visited.add(nxt.dst)
            heapq.heappush(queue, nxt)
    return None
