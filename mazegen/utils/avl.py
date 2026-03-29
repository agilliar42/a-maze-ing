from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator
from typing import Self, cast
import textwrap

from mazegen.utils.coords import CellCoord, SplitWall
from mazegen.utils.ivec2 import IVec2
from mazegen.utils.quadtree import Rect


class Key(ABC):
    """
    This class represents a tree key
    It is expected to be associative but not commutative
    """

    @abstractmethod
    def reconcile(self, rhs: Self) -> Self:
        """
        The function that is called to recompute the parent node as needed
        """


class NoopKey(Key):
    """
    An AVL key that does nothing to reconciliate
    """

    instance: Self | None = None

    def __new__(cls) -> Self:
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def reconcile(self, rhs: Key) -> "NoopKey":
        if not isinstance(rhs, NoopKey):
            raise Exception()
        return self

    def __repr__(self) -> str:
        return "None"


class BVHKey(Key):
    """
    An AVL key that maintains a bounding rectangle for each subtree
    """

    def __init__(self, rect: Rect) -> None:
        super().__init__()
        self.rect: Rect = rect

    @staticmethod
    def for_cell(cell: CellCoord) -> "BVHKey":
        """
        Makes the BVH that corresponds to the given cell
        """
        return BVHKey((cell, cell + IVec2.splat(1)))

    @staticmethod
    def for_wall(wall: SplitWall) -> "BVHKey":
        """
        Makes the BVH that corresponds to the given split wall
        """
        return BVHKey.for_cell(wall[0])

    def reconcile(self, rhs: Key) -> "BVHKey":
        if not isinstance(rhs, BVHKey):
            raise Exception()
        s1, e1 = self.rect
        s2, e2 = rhs.rect
        return BVHKey((s1.lane_min(s2), e1.lane_max(e2)))

    def __repr__(self) -> str:
        return f"{self.rect}"


class Tree[K: Key, V]:
    def __init__(self) -> None:
        self.root: Node[K, V] | None = None

    def __repr__(self) -> str:
        return f"{self.root}" if self.root is not None else "(empty)"

    def validate(self) -> None:
        """
        Checks that the AVL tree is valid and acyclic, for debugging
        """
        if self.root is not None:
            self.root.validate()

    def __iter__(self) -> Iterator[V]:
        if self.root is None:
            return iter(())
        return iter(self.root)

    def append(self, key: K, value: V) -> "Leaf[K, V]":
        """
        Adds the given key and value at the end of the tree, returns the
        created leaf
        """
        if self.root is None:
            leaf = Leaf(self, key, value)
            self.root = leaf
            return leaf
        if isinstance(self.root, Branch):
            return self.root.append(key, value)
        self.root = Branch(
            self,
            self.root.with_parent,
            lambda parent: Leaf(parent, key, value),
        )
        return cast(Leaf[K, V], self.root.rhs)

    def prepend(self, key: K, value: V) -> "Leaf[K, V]":
        """
        Adds the given key and value at the start of the tree, returns the
        created leaf
        """
        if self.root is None:
            leaf = Leaf(self, key, value)
            self.root = leaf
            return leaf
        if isinstance(self.root, Branch):
            return self.root.prepend(key, value)
        self.root = Branch(
            self,
            lambda parent: Leaf(parent, key, value),
            self.root.with_parent,
        )
        return cast(Leaf[K, V], self.root.lhs)

    def height(self) -> int:
        """
        Returns the height of the tree
        """
        return 0 if self.root is None else self.root.height

    def is_empty(self) -> bool:
        """
        Returns whether this tree is empty
        """
        return self.root is None

    def replace(self, node: "Node[K, V]", by: "Node[K, V]") -> None:
        """
        Replace a node by another in this node's children, asserting it is
        present
        """
        if node is not self.root:
            raise Exception("Replace operation with unknown node")
        self.root = by
        by.parent = self

    def balance_update_propagate(self) -> None:
        """
        Propagate the balance update of the tree upwards if needed
        """
        return

    def exchange(self, other: "Tree[K, V]") -> None:
        """
        Exchange the two trees' roots in-place
        """
        a = self.root
        b = other.root
        if a is not None:
            a = a.with_parent(other)
        if b is not None:
            b = b.with_parent(self)
        other.root = a
        self.root = b

    def ljoin(self, lhs: "Tree[K, V]") -> None:
        """
        Joins the tree to the left of self
        """
        if self is lhs:
            raise Exception("Cannot merge tree with itself")
        if self.height() >= lhs.height():
            self.__ljoin(lhs)
        else:
            lhs.__rjoin(self)
            self.exchange(lhs)

    def rjoin(self, rhs: "Tree[K, V]") -> None:
        """
        Joins the tree to the right of self
        """
        if self is rhs:
            raise Exception("Cannot merge tree with itself")
        if self.height() >= rhs.height():
            self.__rjoin(rhs)
        else:
            rhs.__ljoin(self)
            self.exchange(rhs)

    def __ljoin(self, lhs: "Tree[K, V]") -> None:
        """
        Joins the tree to the left of self, assuming self is taller than lhs
        """
        if self.root is None:
            self.exchange(lhs)
        if self.root is None or lhs.root is None:
            return
        curr = self.root
        insert = lhs.root
        lhs.root = None
        while isinstance(curr, Branch) and curr.height > insert.height:
            curr = curr.lhs
        parent = curr.parent
        new = Branch(
            parent,
            insert.with_parent,
            curr.with_parent,
        )
        parent.replace(curr, new)
        new.update_height()
        parent.balance_update_propagate()

    def __rjoin(self, rhs: "Tree[K, V]") -> None:
        """
        Joins the tree to the right of self, assuming self is taller than rhs
        """
        if self.root is None:
            self.exchange(rhs)
        if self.root is None or rhs.root is None:
            return
        curr = self.root
        insert = rhs.root
        rhs.root = None
        while isinstance(curr, Branch) and curr.height > insert.height:
            curr = curr.rhs
        parent = curr.parent
        new = Branch(
            parent,
            curr.with_parent,
            insert.with_parent,
        )
        parent.replace(curr, new)
        new.update_height()
        parent.balance_update_propagate()


class Node[K: Key, V](ABC):
    """
    The abstract class of a node in an AVL tree
    """

    __slots__: tuple[str, ...] = ("parent", "height", "key")

    def __init__(self, parent: "Branch[K, V] | Tree[K, V]", key: K) -> None:
        self.parent: Branch[K, V] | Tree[K, V] = parent
        self.key: K = key
        self.height: int = 1

    @abstractmethod
    def __iter__(self) -> Iterator[V]: ...

    def validate(self) -> None:
        """
        Validates this node by checking it is acyclic for debugging
        """
        visited = set()
        border: list[Node[K, V]] = [self]
        while len(border):
            curr = border.pop()
            if curr in visited:
                raise Exception("Cycle in tree")
            visited.add(curr)
            if isinstance(curr, Branch):
                border.append(curr.lhs)
                border.append(curr.rhs)

    def with_parent(self, parent: "Branch[K, V] | Tree[K, V]") -> "Node[K, V]":
        """
        Changes this node's parent and return self
        """
        self.parent = parent
        return self

    def root(self) -> Tree[K, V]:
        """
        Get the root of the tree this node belongs to
        """
        if isinstance(self.parent, Tree):
            return self.parent
        return self.parent.root()

    def remove(self) -> None:
        """
        Removes this leaf from this node's parent tree
        """
        if isinstance(self.parent, Tree):
            self.parent.root = None
            return
        other = self.parent.get_other(self)
        self.parent.parent.replace(self.parent, other)
        other.parent.balance_update_propagate()

    def split_up(self) -> tuple[Tree[K, V], Tree[K, V]]:
        """
        Makes the root of this tree empty, and returns two trees which
        maintain the order of the previous, left and right of this node
        respectively
        """
        curr = self
        lhs = Tree[K, V]()
        rhs = Tree[K, V]()
        while isinstance(curr.parent, Node):
            curr_parent = curr.parent
            extra = Tree[K, V]()
            if curr_parent.lhs is curr:
                extra.root = curr_parent.rhs.with_parent(extra)
                rhs.rjoin(extra)
            elif curr_parent.rhs is curr:
                extra.root = curr_parent.lhs.with_parent(extra)
                lhs.ljoin(extra)
            else:
                raise Exception("Invalid AVL structure")
            curr = curr_parent
        curr.parent.root = None
        return (lhs, rhs)


class Branch[K: Key, V](Node[K, V]):
    """
    A branch in an AVL tree, which necessarily has two children
    """

    __slots__: tuple[str, ...] = ("lhs", "rhs")

    def __init__(
        self,
        parent: "Branch[K, V] | Tree[K, V]",
        lhs: Callable[["Branch[K, V]"], Node[K, V]],
        rhs: Callable[["Branch[K, V]"], Node[K, V]],
    ) -> None:
        self.lhs: Node[K, V] = lhs(self)
        self.rhs: Node[K, V] = rhs(self)
        super().__init__(parent, self.lhs.key.reconcile(self.rhs.key))
        self.update_height()

    def __iter__(self) -> Iterator[V]:
        for e in self.lhs:
            yield e
        for e in self.rhs:
            yield e

    def __repr__(self) -> str:
        return (
            f"lhs ({self.lhs.height}):\n"
            + textwrap.indent(str(self.lhs), "|   ")
            + f"\nrhs ({self.rhs.height}):\n"
            + textwrap.indent(str(self.rhs), "    ")
        )

    def replace(self, node: Node[K, V], by: Node[K, V]) -> None:
        """
        Replace a node by another in this node's children, asserting it is
        present
        """
        if self.lhs is node:
            self.lhs = by
        elif self.rhs is node:
            self.rhs = by
        else:
            raise Exception("Replace operation with unknown node")
        by.parent = self

    def get_other(self, node: Node[K, V]) -> Node[K, V]:
        """
        Returns the node that is not the given one in this branche's children
        """
        if self.lhs is node:
            return self.rhs
        elif self.rhs is node:
            return self.lhs
        else:
            raise Exception("Get other operation with unknown node")

    def update_height(self) -> None:
        """
        Update this branch's height from its children
        """
        self.height = max(self.lhs.height, self.rhs.height) + 1

    def update_key(self) -> None:
        """
        Update this branche's key from its children
        """
        self.key = self.lhs.key.reconcile(self.rhs.key)

    def get_balance(self) -> int:
        """
        Returns the AVL balance of this node
        """
        return self.rhs.height - self.lhs.height

    def rotate_rr(self) -> None:
        """
        Rotates the subtree such that the right node of the right node is
        lifted up
        """
        # Simple AVL rotate:
        #
        #   n     -->     m
        #  / \           / \
        # a   m         n   c
        #    / \       / \
        #   b   c     a   b
        parent = self.parent
        n = self
        m = n.rhs
        if not isinstance(m, Branch):
            return
        a = n.lhs
        b = m.lhs
        c = m.rhs
        n.lhs = a
        n.rhs = b
        m.lhs = n
        m.rhs = c
        a.parent = n
        b.parent = n
        c.parent = m
        n.parent = m
        n.update_height()
        m.update_height()
        n.update_key()
        m.update_key()
        m.parent = parent
        m.parent.replace(self, m)

    def rotate_ll(self) -> None:
        """
        Rotates the subtree such that the left node of the left node is
        lifted up
        """
        # Simple AVL rotate:
        #
        #     m   -->   n
        #    / \       / \
        #   n   c     a   m
        #  / \           / \
        # a   b         b   c
        parent = self.parent
        m = self
        n = m.lhs
        if not isinstance(n, Branch):
            return
        a = n.lhs
        b = n.rhs
        c = m.rhs
        n.lhs = a
        n.rhs = m
        m.lhs = b
        m.rhs = c
        a.parent = n
        b.parent = m
        c.parent = m
        m.parent = n
        n.update_height()
        m.update_height()
        n.update_key()
        m.update_key()
        n.parent = parent
        n.parent.replace(self, n)

    def rotate_rl(self) -> None:
        """
        Rotates the subtree such that the left node of the right node is
        lifted up
        """
        # Double AVL rotate:
        #
        #   n     -->   n       -->      m
        #  / \         / \              / \
        # a   o       a   m            /   \
        #    / \         / \          n     o
        #   m   d       b   o        / \   / \
        #  / \             / \      a   b c   d
        # b   c           c   d
        m = self.rhs
        if not isinstance(m, Branch):
            return
        m.rotate_ll()
        self.rotate_rr()

    def rotate_lr(self) -> None:
        """
        Rotates the subtree such that the right node of the left node is
        lifted up
        """
        # Double AVL rotate:
        #
        #     o   -->       o   -->      m
        #    / \           / \          / \
        #   n   d         m   d        /   \
        #  / \           / \          n     o
        # a   m         n   c        / \   / \
        #    / \       / \          a   b c   d
        #   b   c     a   b
        n = self.lhs
        if not isinstance(n, Branch):
            return
        n.rotate_rr()
        self.rotate_ll()
        n = self.lhs

    def append(self, key: K, value: V) -> "Leaf[K, V]":
        """
        Append the given key and value to the end of this subtree
        """
        if isinstance(self.rhs, Branch):
            return self.rhs.append(key, value)
        new = Branch[K, V](
            self,
            self.rhs.with_parent,
            lambda parent: Leaf[K, V](parent, key, value),
        )
        self.rhs = new
        new_leaf = cast(Leaf[K, V], new.rhs)
        self.balance_update_propagate()
        return new_leaf

    def prepend(self, key: K, value: V) -> "Leaf[K, V]":
        """
        Prepend the given key and value to the end of this subtree
        """
        if isinstance(self.lhs, Branch):
            return self.lhs.prepend(key, value)
        new = Branch[K, V](
            self,
            lambda parent: Leaf[K, V](parent, key, value),
            self.lhs.with_parent,
        )
        self.lhs = new
        new_leaf = cast(Leaf[K, V], new.lhs)
        self.balance_update_propagate()
        return new_leaf

    def balance_one(self) -> None:
        """
        Balances, if necessary, the left and right hand sides of this subtree,
        through AVL rotations
        """
        if abs(self.get_balance()) <= 1:
            return

        if self.get_balance() > 0:
            # right is taller
            if not isinstance(self.rhs, Branch):
                raise Exception("Invalid tree state")
            if self.rhs.get_balance() >= 0:
                self.rotate_rr()
            else:
                self.rotate_rl()
        else:
            # left is taller
            if not isinstance(self.lhs, Branch):
                raise Exception("Invalid tree state")
            if self.lhs.get_balance() >= 0:
                self.rotate_lr()
            else:
                self.rotate_ll()

    def balance_update_propagate(self) -> None:
        """
        Balance this subtree, then propagate up if necessary
        """
        init_height = self.height
        init_key = self.key
        self.update_height()
        self.update_key()
        self.balance_one()
        if init_height != self.height or init_key != self.key:
            self.parent.balance_update_propagate()


class Leaf[K: Key, V](Node[K, V]):
    """
    A leaf in an AVL Tree
    """

    __slots__: tuple[str, ...] = ("value",)

    def __init__(
        self,
        parent: Branch[K, V] | Tree[K, V],
        key: K,
        value: V,
    ) -> None:
        super().__init__(parent, key)
        self.value: V = value

    def __iter__(self) -> Iterator[V]:
        yield self.value

    def __repr__(self) -> str:
        return f"leaf ({self.key}): {self.value}"
