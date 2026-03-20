from collections.abc import Callable
from typing import assert_never, cast
from amazeing.maze_display.backend import IVec2
from functools import partial
from itertools import chain

type tuple4[T] = tuple[T, T, T, T]


def map4[T, U](fn: Callable[[T], U], tup: tuple4[T]) -> tuple4[U]:
    return cast(tuple4[U], tuple(map(fn, tup)))


def zip4[T, U](a: tuple4[T], b: tuple4[U]) -> tuple4[tuple[T, U]]:
    return cast(tuple4[tuple[T, U]], tuple(zip(a, b)))


type Node = tuple4[MaybeNode]
type MaybeNode = Node | bool

# start, end
type Rect = tuple[IVec2, IVec2]


def rect_collide(a: Rect, b: Rect) -> bool:
    a_start, a_end = a
    b_start, b_end = b
    return (
        a_end.x > b_start.x
        and a_end.y > b_start.y
        and b_end.x > a_start.x
        and b_end.y > a_start.y
    )


def rect_contains(a: Rect, b: Rect) -> bool:
    a_start, a_end = a
    b_start, b_end = b
    return (
        a_start.x <= b_start.x
        and a_start.y <= b_start.y
        and a_end.x >= b_end.x
        and a_end.y >= b_end.y
    )


class Tree:
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
        res = Tree(self)
        while res.__height < target:
            res.__root = (self.__root, False, False, False)
            res.__height += 1
        return res

    def normalized(self) -> "Tree":
        res = Tree(self)
        while True:
            match res.__root:
                case (e, False, False, False):
                    res.__height -= 1
                    res.__root = e
                case _:
                    return res

    def shared_layer_apply(
        self, fn: Callable[[MaybeNode, MaybeNode], MaybeNode], other: "Tree"
    ) -> "Tree":
        res = self.raised_to(other.__height)

        def descend(node: MaybeNode, depth: int = 0) -> MaybeNode:
            if other.__height + depth == self.__height:
                return fn(node, other.__root)
            (a, b, c, d) = Tree.node_split(node)
            a = descend(a, depth + 1)
            return Tree.node_normalize((a, b, c, d))

        res.__root = descend(self.__root)
        return res.normalized()

    def __or__(self, other: "Tree") -> "Tree":
        return self.shared_layer_apply(Tree.node_union, other)

    def __and__(self, other: "Tree") -> "Tree":
        return self.shared_layer_apply(Tree.node_intersection, other)

    @staticmethod
    def rectangle(rect: Rect) -> "Tree":
        res = Tree()
        while (s := 1 << res.__height) < rect[1].x or s < rect[1].y:
            res.__height += 1
        res.__root = Tree.node_from_rect(IVec2(0, 0), res.__height, rect)
        return res

    @staticmethod
    def node_to_tab(node: MaybeNode, height: int) -> list[list[bool]]:
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
        match node:
            case (True, True, True, True):
                return True
            case (False, False, False, False):
                return False
        return node

    @staticmethod
    def node_split(node: MaybeNode) -> Node:
        match node:
            case True:
                return (True, True, True, True)
            case False:
                return (False, False, False, False)
        return node

    @staticmethod
    def node_from_rect(pos: IVec2, height: int, rect: Rect) -> MaybeNode:
        node_rect = Tree.node_rect(pos, height)
        if rect_contains(rect, node_rect):
            return True
        if not rect_collide(rect, node_rect):
            return False
        starts = Tree.node_starts(pos, height)
        return map4(
            partial(Tree.node_from_rect, height=height - 1, rect=rect),
            starts,
        )

    @staticmethod
    def node_rect(pos: IVec2, height: int) -> Rect:
        return (pos, pos + IVec2.splat(1 << height))

    @staticmethod
    def node_starts(pos: IVec2, height: int) -> tuple4[IVec2]:
        dims = IVec2.splat(1 << (height - 1))

        def f(x: int, y: int) -> IVec2:
            return pos + IVec2(x, y) * dims

        return (
            f(0, 0),
            f(1, 0),
            f(0, 1),
            f(1, 1),
        )

    @staticmethod
    def node_negation(node: MaybeNode) -> MaybeNode:
        if isinstance(node, bool):
            return not node
        return map4(Tree.node_negation, node)

    @staticmethod
    def node_union(a: MaybeNode, b: MaybeNode) -> MaybeNode:
        match (a, b):
            case (True, _) | (_, True):
                return True
            case (False, n) | (n, False):
                return n
            case (a, b):
                return Tree.node_normalize(
                    map4(lambda e: Tree.node_union(*e), zip4(a, b))
                )
        # mypy please do proper control flow analysis
        raise Exception()

    @staticmethod
    def node_intersection(a: MaybeNode, b: MaybeNode) -> MaybeNode:
        match (a, b):
            case (False, _) | (_, False):
                return False
            case (True, n) | (n, True):
                return n
            case (a, b):
                return Tree.node_normalize(
                    map4(lambda e: Tree.node_intersection(*e), zip4(a, b))
                )
        # ditto
        raise Exception()
