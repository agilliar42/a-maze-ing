from mazegen.maze import Maze
from mazegen.utils.coords import (
    split_wall_ccw,
    split_wall_opposite,
)
from mazegen.utils import AVLTree, AVLLeaf, SplitWall, WallCoord
from mazegen.utils.avl import BVHKey
from mazegen.utils.quadtree import Rect


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
        self.__trees: set[AVLTree[BVHKey, SplitWall]] = set()
        self.__revmap: dict[SplitWall, AVLLeaf[BVHKey, SplitWall]] = {}

    def __repr__(self) -> str:
        return (
            f"DualForest ({len(self.__trees)}):\n    trees:\n"
            + f"{self.__trees}\n    revmap:\n{self.__revmap}\n"
        )

    def find_split(
        self,
        split_wall: SplitWall,
    ) -> SplitWall | None:
        split_wall = split_wall_opposite(split_wall)
        for _ in range(3):
            split_wall = split_wall_ccw(split_wall)
            if split_wall in self.__revmap:
                return split_wall
        return None

    def fill_wall(self, wall: WallCoord) -> None:
        if self.get_wall(wall):
            return
        a_wall, b_wall = wall.to_split_wall()
        a_tree = AVLTree[BVHKey, SplitWall]()
        b_tree = AVLTree[BVHKey, SplitWall]()
        self.__revmap[a_wall] = a_tree.append(BVHKey.for_wall(a_wall), a_wall)
        self.__revmap[b_wall] = b_tree.append(BVHKey.for_wall(b_wall), b_wall)

        match (self.find_split(a_wall), self.find_split(b_wall)):
            case (None, None):
                a_tree.rjoin(b_tree)
                self.__trees.add(a_tree)
            case (None, b_split):
                # mypy is stupid
                if b_split is None:
                    raise Exception()
                b_leaf = self.__revmap.pop(b_split)
                self.__trees.remove(b_leaf.root())
                lhs, rhs = b_leaf.split_up()
                lhs.rjoin(a_tree)
                lhs.rjoin(b_tree)
                self.__revmap[b_split] = lhs.append(
                    BVHKey.for_wall(b_split), b_split
                )
                lhs.rjoin(rhs)
                self.__trees.add(lhs)
            case (a_split, None):
                # mypy is stupid
                if a_split is None:
                    raise Exception()
                a_leaf = self.__revmap.pop(a_split)
                self.__trees.remove(a_leaf.root())
                lhs, rhs = a_leaf.split_up()
                lhs.rjoin(b_tree)
                lhs.rjoin(a_tree)
                self.__revmap[a_split] = lhs.append(
                    BVHKey.for_wall(a_split), a_split
                )
                lhs.rjoin(rhs)
                self.__trees.add(lhs)
            case (a_split, b_split):
                # mypy is stupid
                if a_split is None or b_split is None:
                    raise Exception()
                a_leaf, b_leaf = self.__revmap.pop(a_split), self.__revmap.pop(
                    b_split
                )
                if a_leaf.root() is b_leaf.root():
                    self.__trees.remove(a_leaf.root())
                    lhs, rhs = a_leaf.split_up()
                    lhs.rjoin(b_tree)
                    self.__revmap[a_split] = rhs.prepend(
                        BVHKey.for_wall(a_split), a_split
                    )
                    rhs.ljoin(a_tree)
                    rhs.rjoin(lhs)
                    lhs, rhs = b_leaf.split_up()
                    self.__revmap[b_split] = rhs.prepend(
                        BVHKey.for_wall(b_split), b_split
                    )
                    self.__trees.add(lhs)
                    self.__trees.add(rhs)
                else:
                    self.__trees.remove(a_leaf.root())
                    self.__trees.remove(b_leaf.root())
                    a_lhs, a_rhs = a_leaf.split_up()
                    b_lhs, b_rhs = b_leaf.split_up()
                    self.__revmap[a_split] = a_rhs.prepend(
                        BVHKey.for_wall(a_split), a_split
                    )
                    self.__revmap[b_split] = b_rhs.prepend(
                        BVHKey.for_wall(b_split), b_split
                    )
                    res = a_lhs
                    res.rjoin(b_tree)
                    res.rjoin(b_rhs)
                    res.rjoin(b_lhs)
                    res.rjoin(a_tree)
                    res.rjoin(a_rhs)
                    self.__trees.add(res)

    def empty_wall(self, wall: WallCoord) -> None:
        if not self.get_wall(wall):
            return
        a_wall, b_wall = wall.to_split_wall()
        a_leaf, b_leaf = self.__revmap.pop(a_wall), self.__revmap.pop(b_wall)
        if a_leaf.root() is b_leaf.root():
            self.__trees.remove(a_leaf.root())
            lhs, rhs = a_leaf.split_up()
            rhs.rjoin(lhs)
            a_res, b_res = b_leaf.split_up()
            if a_res.height() > 0:
                self.__trees.add(a_res)
            if b_res.height() > 0:
                self.__trees.add(b_res)
        else:
            self.__trees.remove(a_leaf.root())
            self.__trees.remove(b_leaf.root())
            a_lhs, a_rhs = a_leaf.split_up()
            b_lhs, b_rhs = b_leaf.split_up()
            res = AVLTree[BVHKey, SplitWall]()
            res.rjoin(a_lhs)
            res.rjoin(b_rhs)
            res.rjoin(b_lhs)
            res.rjoin(a_rhs)
            if res.height() > 0:
                self.__trees.add(res)

    def get_wall(self, wall: WallCoord) -> bool:
        a_wall, b_wall = wall.to_split_wall()
        return a_wall in self.__revmap and b_wall in self.__revmap

    def contour_bound(self, wall: SplitWall) -> Rect | None:
        if wall not in self.__revmap:
            return None
        leaf = self.__revmap[wall]
        parent = leaf.root()
        if parent.root is None:
            raise Exception()
        return parent.root.key.rect

    def wall_bisects(self, wall: WallCoord) -> bool:
        a_wall, b_wall = wall.to_split_wall()
        a_split = self.find_split(a_wall)
        b_split = self.find_split(b_wall)
        if a_split is None or b_split is None:
            return False
        a_leaf, b_leaf = self.__revmap[a_split], self.__revmap[b_split]
        if self.get_wall(wall):
            return a_leaf.root() is not b_leaf.root()
        else:
            return a_leaf.root() is b_leaf.root()


class NetworkTracker:
    def __init__(self, maze: Maze) -> None:
        self.__maze: Maze = maze
        self.__forest: DualForest = DualForest()

        maze.observers.add(self.__observer)
        for wall in maze.walls_full():
            self.__observer(wall)

    def __observer(self, wall: WallCoord) -> None:
        if self.__maze.get_wall(wall):
            self.__forest.fill_wall(wall)
        else:
            self.__forest.empty_wall(wall)

    def wall_bisects(self, wall: WallCoord) -> bool:
        return self.__forest.wall_bisects(wall)

    def contour_bound(self, wall: SplitWall) -> Rect | None:
        return self.__forest.contour_bound(wall)

    def end(self) -> None:
        self.__maze.observers.discard(self.__observer)
