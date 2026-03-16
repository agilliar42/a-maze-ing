from amazeing.maze_class.maze import Maze
from amazeing.maze_class.maze_coords import (
    Cardinal,
    CellCoord,
    SplitWall,
    WallCoord,
    split_wall_ccw,
    split_wall_opposite,
)
from amazeing.utils import BiMap
from amazeing.utils import AVLTree, AVLLeaf


class NetworkID:
    pass


class DualForest:
    """
    A forest of trees that contour networks
    AVL trees are used to represent the contours, such that split and
    merge operations are of complexity O(log n), each tree is a cycle
    of each connex graph boundary
    """

    def __init__(
        self,
    ) -> None:
        # Trees are left hand chiral
        self.__trees: set[AVLTree[SplitWall]] = set()
        self.__revmap: dict[SplitWall, AVLLeaf[SplitWall]] = {}

    def __repr__(self) -> str:
        return (
            f"DualForest ({len(self.__trees)}):\n    trees:\n"
            + f"{self.__trees}\n    revmap:\n{self.__revmap}\n"
        )

    def fill_wall(self, wall: WallCoord) -> None:
        lhs, rhs = wall.to_split_wall()
        if lhs in self.__revmap or rhs in self.__revmap:
            return
        a_tree = AVLTree()
        b_tree = AVLTree()
        self.__revmap[lhs] = a_tree.append(lhs)
        self.__revmap[rhs] = b_tree.append(rhs)

        def find_split(split_wall: SplitWall) -> SplitWall | None:
            split_wall = split_wall_opposite(split_wall)
            for _ in range(3):
                split_wall = split_wall_ccw(split_wall)
                if split_wall in self.__revmap:
                    return split_wall
            return None

        match (find_split(lhs), find_split(rhs)):
            case (None, None):
                a_tree.rjoin(b_tree)
                self.__trees.add(a_tree)
            case (None, b_split):
                self.__trees.remove(self.__revmap[b_split].root())
                lhs, rhs = self.__revmap[b_split].split_up()
                lhs.rjoin(a_tree)
                lhs.rjoin(b_tree)
                self.__revmap[b_split] = lhs.append(b_split)
                lhs.rjoin(rhs)
                self.__trees.add(lhs)
            case (a_split, None):
                self.__trees.remove(self.__revmap[a_split].root())
                lhs, rhs = self.__revmap[a_split].split_up()
                lhs.rjoin(b_tree)
                lhs.rjoin(a_tree)
                self.__revmap[a_split] = lhs.append(a_split)
                lhs.rjoin(rhs)
                self.__trees.add(lhs)
            case (a_split, b_split):
                if (
                    self.__revmap[a_split].root()
                    is self.__revmap[b_split].root()
                ):
                    self.__trees.remove(self.__revmap[a_split].root())
                    lhs, rhs = self.__revmap[a_split].split_up()
                    lhs.rjoin(b_tree)
                    self.__revmap[a_split] = rhs.prepend(a_split)
                    rhs.ljoin(a_tree)
                    rhs.rjoin(lhs)
                    lhs, rhs = self.__revmap[b_split].split_up()
                    self.__revmap[b_split] = rhs.prepend(b_split)
                    self.__trees.add(lhs)
                    self.__trees.add(rhs)
                else:
                    self.__trees.remove(self.__revmap[a_split].root())
                    self.__trees.remove(self.__revmap[b_split].root())
                    a_lhs, a_rhs = self.__revmap[a_split].split_up()
                    b_lhs, b_rhs = self.__revmap[b_split].split_up()
                    self.__revmap[a_split] = a_rhs.prepend(a_split)
                    self.__revmap[b_split] = b_rhs.prepend(b_split)
                    res = a_lhs
                    res.rjoin(b_tree)
                    res.rjoin(b_rhs)
                    res.rjoin(b_lhs)
                    res.rjoin(a_tree)
                    res.rjoin(a_rhs)
                    self.__trees.add(res)

    def empty_wall(self, wall: WallCoord) -> None:
        pass


class MazeNetworkTracker:
    def __init__(self, maze: Maze) -> None:
        self.__maze: Maze = maze
        self.__networks_wall: BiMap[NetworkID, WallCoord] = BiMap()
        self.__networks_cell: BiMap[NetworkID, CellCoord] = BiMap()

        netid = NetworkID()
        for cell in maze.all_cells():
            self.__networks_cell.add(netid, cell)

        maze.observers.add(self.__observer)
        for wall in maze.walls_full():
            self.__observer(wall)

    def __observer(self, wall: WallCoord) -> None:
        return

    def end(self):
        self.__maze.observers.discard(self.__observer)
