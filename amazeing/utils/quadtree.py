from typing import cast
from amazeing.maze_display.backend import IVec2
from functools import partial
from itertools import chain

type tuple4[T] = tuple[T, T, T, T]

type Node = tuple4[MaybeNode]
type MaybeNode = Node | bool

# start, end
type Rect = tuple[IVec2, IVec2]


class Tree:
    def __init__(self) -> None:
        self.__root: MaybeNode = False
        self.__height: int = 0

    def __repr__(self) -> str:
        tab = Tree.node_to_tab(self.__root, self.__height)
        data = "\n".join(
            "".join("#" if char else "-" for char in line) for line in tab
        )
        return f"Quadtree: height - {self.__height}, data:\n{data}"

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
    def node_simplify(node: MaybeNode) -> MaybeNode:
        match node:
            case (True, True, True, True):
                return True
            case (False, False, False, False):
                return False
        return node

    @staticmethod
    def node_from_rect(pos: IVec2, height: int, rect: Rect) -> MaybeNode:
        node_rect = Tree.node_rect(pos, height)
        if Tree.rect_contains(rect, node_rect):
            return True
        if not Tree.rect_collide(rect, node_rect):
            return False
        starts = Tree.node_starts(pos, height)
        return cast(
            Node,
            tuple(
                map(
                    partial(Tree.node_from_rect, height=height - 1, rect=rect),
                    starts,
                )
            ),
        )

    @staticmethod
    def node_rect(pos: IVec2, height: int) -> Rect:
        return (pos, pos + IVec2.splat(1 << height))

    @staticmethod
    def node_starts(pos: IVec2, height: int) -> tuple4[IVec2]:
        dims = IVec2.splat(1 << (height - 1))

        def f(x: int, y: int) -> IVec2:
            return pos + IVec2(x, y) * dims

        # fmt: off
        return (
            f(0, 0), f(1, 0),
            f(0, 1), f(1, 1),
        )
        # fmt: on

    @staticmethod
    def rect_collide(a: Rect, b: Rect) -> bool:
        a_start, a_end = a
        b_start, b_end = b
        return (
            a_end.x > b_start.x
            and a_end.y > b_start.y
            and b_end.x > a_start.x
            and b_end.y > a_start.y
        )

    @staticmethod
    def rect_contains(a: Rect, b: Rect) -> bool:
        a_start, a_end = a
        b_start, b_end = b
        return (
            a_start.x <= b_start.x
            and a_start.y <= b_start.y
            and a_end.x >= b_end.x
            and a_end.y >= b_end.y
        )
