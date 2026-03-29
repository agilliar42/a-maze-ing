from collections.abc import Callable, Generator
from mazegen.utils.ivec2 import IVec2
from functools import partial
from itertools import chain

type tuple4[T] = tuple[T, T, T, T]


def map4[T, U](fn: Callable[[T], U], tup: tuple4[T]) -> tuple4[U]:
    """
    Like map, but typed for a tuple4
    """
    a, b, c, d = tup
    return (fn(a), fn(b), fn(c), fn(d))


def zip4[T, U](a: tuple4[T], b: tuple4[U]) -> tuple4[tuple[T, U]]:
    """
    Like zip, but typed for a tuple4
    """
    a1, b1, c1, d1 = a
    a2, b2, c2, d2 = b
    return ((a1, a2), (b1, b2), (c1, c2), (d1, d2))


type Node = tuple4[MaybeNode]
type MaybeNode = Node | bool

# start, end
type Rect = tuple[IVec2, IVec2]


def rects_overlap(a: Rect, b: Rect) -> bool:
    """
    Checks whether two rectangles overlap
    """
    a_start, a_end = a
    b_start, b_end = b
    return (
        a_end.x > b_start.x
        and a_end.y > b_start.y
        and b_end.x > a_start.x
        and b_end.y > a_start.y
    )


def rect_collides(a: Rect, b: IVec2) -> bool:
    """
    Checks whether two rectangles collide
    """
    a_start, a_end = a
    return (
        a_end.x > b.x
        and a_end.y > b.y
        and b.x >= a_start.x
        and b.y >= a_start.y
    )


def rect_contains(a: Rect, b: Rect) -> bool:
    """
    Checks whether a rect contains another
    """
    a_start, a_end = a
    b_start, b_end = b
    return (
        a_start.x <= b_start.x
        and a_start.y <= b_start.y
        and a_end.x >= b_end.x
        and a_end.y >= b_end.y
    )


class Tree:
    """
    A boolean quadtree, with simplification for identical subcells
    """

    def __init__(self, copy: "Tree | None" = None) -> None:
        self.__root: MaybeNode = False
        self.__height: int = 0
        if copy is not None:
            self.__root = copy.__root
            self.__height = copy.__height

    def __repr__(self) -> str:
        tab = Tree.node_to_tab(self.__root, self.__height)
        data = "\n".join(
            "".join("#" if char else "-" for char in line) for line in tab
        )
        return f"Quadtree: height - {self.__height}, data:\n{data}"

    def raised_to(self, target: int) -> "Tree":
        """
        Increase the height of this tree and extend it to reach at least
        target height
        """
        res = Tree(self)
        while res.__height < target:
            res.__root = (self.__root, False, False, False)
            res.__height += 1
        return res

    def normalized(self) -> "Tree":
        """
        Lowers the tree for as long as can be simplified, to reach a canonical
        form
        """
        res = Tree(self)
        while True:
            match res.__root:
                case (e, False, False, False):
                    res.__height -= 1
                    res.__root = e
                case False:
                    res.__height = 0
                    return res
                case _:
                    return res

    def shared_layer_apply(
        self, fn: Callable[[MaybeNode, MaybeNode], MaybeNode], other: "Tree"
    ) -> "Tree":
        """
        Applies the given function between two nodes that are at the same
        layer and thus position
        """
        res = self.raised_to(other.__height)

        def descend(node: MaybeNode, depth: int = 0) -> MaybeNode:
            if other.__height + depth == res.__height:
                return fn(node, other.__root)
            (a, b, c, d) = Tree.node_split(node)
            a = descend(a, depth + 1)
            return Tree.node_normalize((a, b, c, d))

        res.__root = descend(res.__root)
        return res.normalized()

    def __or__(self, other: "Tree") -> "Tree":
        return self.shared_layer_apply(Tree.node_or, other)

    def __and__(self, other: "Tree") -> "Tree":
        return self.shared_layer_apply(Tree.node_and, other)

    def __add__(self, other: "Tree") -> "Tree":
        return self | other

    def __sub__(self, other: "Tree") -> "Tree":
        return self.shared_layer_apply(Tree.node_sub, other)

    def tiles(self) -> Generator[IVec2]:
        return Tree.node_tiles(self.__root, IVec2.splat(0), self.__height)

    @staticmethod
    def node_tiles(
        node: MaybeNode, pos: IVec2, height: int
    ) -> Generator[IVec2]:
        """
        Iterates over the tile coords of a given node with a given position
        and height
        """
        if height == 0 and node is True:
            yield pos
        if height == 0 or node is False:
            return
        for pos, node in zip4(
            Tree.node_starts(pos, height), Tree.node_split(node)
        ):
            for pos in Tree.node_tiles(node, pos, height - 1):
                yield pos

    @staticmethod
    def rectangle(rect: Rect) -> "Tree":
        """
        Creates a tree that contains exactly a rectangle
        """
        res = Tree()
        while (s := 1 << res.__height) < rect[1].x or s < rect[1].y:
            res.__height += 1
        res.__root = Tree.node_from_rect(IVec2(0, 0), res.__height, rect)
        return res

    @staticmethod
    def node_to_tab(node: MaybeNode, height: int) -> list[list[bool]]:
        """
        Creates a two dimensional array of booleans corresponding to this node
        """
        if isinstance(node, bool):
            dim = 1 << height
            return [[node for _ in range(dim)] for _ in range(dim)]
        a, b, c, d = node
        subtab = partial(Tree.node_to_tab, height=height - 1)
        return [
            l1 + l2
            for l1, l2 in chain(
                zip(subtab(a), subtab(b)),
                zip(subtab(c), subtab(d)),
            )
        ]

    @staticmethod
    def node_normalize(node: MaybeNode) -> MaybeNode:
        """
        Normalize this node by simlpifying when possible
        """
        match node:
            case (True, True, True, True):
                return True
            case (False, False, False, False):
                return False
        return node

    @staticmethod
    def node_split(node: MaybeNode) -> Node:
        """
        Split this node once, unsimplifying it
        """
        match node:
            case True:
                return (True, True, True, True)
            case False:
                return (False, False, False, False)
        return node

    @staticmethod
    def node_from_rect(pos: IVec2, height: int, rect: Rect) -> MaybeNode:
        """
        Creates a node from a rectangle and is position, such that it fills
        its overlapping region with that rectagle
        """
        node_rect = Tree.node_rect(pos, height)
        if rect_contains(rect, node_rect):
            return True
        if not rects_overlap(rect, node_rect):
            return False
        starts = Tree.node_starts(pos, height)
        return map4(
            partial(Tree.node_from_rect, height=height - 1, rect=rect),
            starts,
        )

    @staticmethod
    def node_rect(pos: IVec2, height: int) -> Rect:
        """
        Returns the rectangle corresponding to a node's position and height
        """
        return (pos, pos + IVec2.splat(1 << height))

    @staticmethod
    def node_starts(pos: IVec2, height: int) -> tuple4[IVec2]:
        """
        Return the start of each sub-node of a node
        """
        dim = 1 << (height - 1)
        x = IVec2(dim, 0)
        y = IVec2(0, dim)

        return (
            pos,
            e := pos + x,
            pos + y,
            e + y,
        )

    @staticmethod
    def node_neg(node: MaybeNode) -> MaybeNode:
        """
        Inverts a node
        """
        if isinstance(node, bool):
            return not node
        return map4(Tree.node_neg, node)

    @staticmethod
    def node_or(a: MaybeNode, b: MaybeNode) -> MaybeNode:
        """
        Applies a boolean or between two nodes
        """
        match (a, b):
            case (True, _) | (_, True):
                return True
            case (False, n) | (n, False):
                return n
            case (a, b):
                return Tree.node_normalize(
                    map4(lambda e: Tree.node_or(*e), zip4(a, b))
                )
        # mypy please do proper control flow analysis
        raise Exception()

    @staticmethod
    def node_and(a: MaybeNode, b: MaybeNode) -> MaybeNode:
        """
        Applies a boolean and between two nodes
        """
        match (a, b):
            case (False, _) | (_, False):
                return False
            case (True, n) | (n, True):
                return n
            case (a, b):
                return Tree.node_normalize(
                    map4(lambda e: Tree.node_and(*e), zip4(a, b))
                )
        # ditto
        raise Exception()

    @staticmethod
    def node_sub(a: MaybeNode, b: MaybeNode) -> MaybeNode:
        """
        Substracts another node from a first
        """
        match (a, b):
            case (False, _) | (_, True):
                return False
            case (n, False):
                return n
            case (True, n):
                return Tree.node_neg(n)
            case (a, b):
                return Tree.node_normalize(
                    map4(lambda e: Tree.node_sub(*e), zip4(a, b))
                )
        # ditto
        raise Exception()
