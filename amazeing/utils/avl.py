from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator
from typing import cast
import textwrap


class Tree[T]:
    def __init__(self) -> None:
        self.root: Node[T] | None = None

    def __repr__(self) -> str:
        return f"{self.root}" if self.root is not None else "(empty)"

    def validate(self) -> None:
        if self.root is not None:
            self.root.validate()

    def __iter__(self) -> Iterator[T]:
        if self.root is None:
            return iter(())
        return iter(self.root)

    def append(self, value: T) -> "Leaf[T]":
        if self.root is None:
            leaf = Leaf(self, value)
            self.root = leaf
            return leaf
        if isinstance(self.root, Branch):
            return self.root.append(value)
        self.root = Branch(
            self,
            self.root.with_parent,
            lambda parent: Leaf(parent, value),
        )
        return cast(Leaf[T], self.root.rhs)

    def prepend(self, value: T) -> "Leaf[T]":
        if self.root is None:
            leaf = Leaf(self, value)
            self.root = leaf
            return leaf
        if isinstance(self.root, Branch):
            return self.root.prepend(value)
        self.root = Branch(
            self,
            lambda parent: Leaf(parent, value),
            self.root.with_parent,
        )
        return cast(Leaf[T], self.root.lhs)

    def height(self) -> int:
        return 0 if self.root is None else self.root.height

    def is_empty(self) -> bool:
        return self.root is None

    def replace(self, node: "Node[T]", by: "Node[T]") -> None:
        if node is not self.root:
            raise Exception("Replace operation with unknown node")
        self.root = by
        by.parent = self

    def balance_one_propagate(self) -> None:
        return

    def exchange(self, other: "Tree[T]") -> None:
        a = self.root
        b = other.root
        if a is not None:
            a = a.with_parent(other)
        if b is not None:
            b = b.with_parent(self)
        other.root = a
        self.root = b

    def ljoin(self, lhs: "Tree[T]") -> None:
        if self is lhs:
            raise Exception("Cannot merge tree with itself")
        if self.height() >= lhs.height():
            self.__ljoin(lhs)
        else:
            lhs.__rjoin(self)
            self.exchange(lhs)

    def rjoin(self, rhs: "Tree[T]") -> None:
        if self is rhs:
            raise Exception("Cannot merge tree with itself")
        if self.height() >= rhs.height():
            self.__rjoin(rhs)
        else:
            rhs.__ljoin(self)
            self.exchange(rhs)

    def __ljoin(self, lhs: "Tree[T]") -> None:
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
        new = Branch(parent, insert.with_parent, curr.with_parent)
        parent.replace(curr, new)
        new.update_height()
        parent.balance_one_propagate()

    def __rjoin(self, rhs: "Tree[T]") -> None:
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
        new = Branch(parent, curr.with_parent, insert.with_parent)
        parent.replace(curr, new)
        new.update_height()
        parent.balance_one_propagate()


class Node[T](ABC):
    def __init__(self, parent: "Branch[T] | Tree[T]") -> None:
        self.parent: Branch[T] | Tree[T] = parent
        self.height: int = 1

    @abstractmethod
    def __iter__(self) -> Iterator[T]: ...

    def validate(self) -> None:
        visited = set()
        border: list[Node[T]] = [self]
        while len(border):
            curr = border.pop()
            if curr in visited:
                raise Exception("Cycle in tree")
            visited.add(curr)
            if isinstance(curr, Branch):
                border.append(curr.lhs)
                border.append(curr.rhs)

    def with_parent(self, parent: "Branch[T] | Tree[T]") -> "Node[T]":
        self.parent = parent
        return self

    def root(self) -> Tree[T]:
        if isinstance(self.parent, Tree):
            return self.parent
        return self.parent.root()

    def split_up(self) -> tuple[Tree[T], Tree[T]]:
        """
        makes self.parent empty
        """
        curr = self
        lhs = Tree[T]()
        rhs = Tree[T]()
        while isinstance(curr.parent, Node):
            curr_parent = curr.parent
            extra = Tree[T]()
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


class Branch[T](Node[T]):
    def __init__(
        self,
        parent: "Branch[T] | Tree[T]",
        lhs: Callable[["Branch[T]"], Node[T]],
        rhs: Callable[["Branch[T]"], Node[T]],
    ) -> None:
        super().__init__(parent)
        self.lhs: Node[T] = lhs(self)
        self.rhs: Node[T] = rhs(self)
        self.update_height()

    def __iter__(self) -> Iterator[T]:
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

    def replace(self, node: Node[T], by: Node[T]) -> None:
        if self.lhs is node:
            self.lhs = by
        elif self.rhs is node:
            self.rhs = by
        else:
            raise Exception("Replace operation with unknown node")
        by.parent = self

    def get_other(self, node: Node[T]) -> Node[T]:
        if self.lhs is node:
            return self.rhs
        elif self.rhs is node:
            return self.lhs
        else:
            raise Exception("Get other operation with unknown node")

    def update_height(self) -> None:
        self.height = max(self.rhs.height, self.lhs.height) + 1

    def get_balance(self) -> int:
        return self.rhs.height - self.lhs.height

    def rotate_rr(self) -> None:
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
        m.parent = parent
        m.parent.replace(self, m)

    def rotate_ll(self) -> None:
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
        n.parent = parent
        n.parent.replace(self, n)

    def rotate_rl(self) -> None:
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

    def append(self, value: T) -> "Leaf[T]":
        if isinstance(self.rhs, Branch):
            return self.rhs.append(value)
        new = Branch[T](
            self,
            self.rhs.with_parent,
            lambda parent: Leaf[T](parent, value),
        )
        self.rhs = new
        new_leaf = cast(Leaf[T], new.rhs)
        self.balance_one_propagate()
        return new_leaf

    def prepend(self, value: T) -> "Leaf[T]":
        if isinstance(self.lhs, Branch):
            return self.lhs.prepend(value)
        new = Branch[T](
            self,
            lambda parent: Leaf[T](parent, value),
            self.lhs.with_parent,
        )
        self.lhs = new
        new_leaf = cast(Leaf[T], new.lhs)
        self.balance_one_propagate()
        return new_leaf

    def balance_one(self) -> None:
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

    def balance_one_propagate(self) -> None:
        init_height = self.height
        self.update_height()
        self.balance_one()
        if init_height != self.height:
            self.parent.balance_one_propagate()


class Leaf[T](Node[T]):
    def __init__(
        self,
        parent: Branch[T] | Tree[T],
        value: T,
    ) -> None:
        super().__init__(parent)
        self.value: T = value

    def __iter__(self) -> Iterator[T]:
        yield self.value

    def __repr__(self) -> str:
        return f"leaf: {self.value}"

    def remove(self) -> None:
        if isinstance(self.parent, Tree):
            self.parent.root = None
            return
        other = self.parent.get_other(self)
        self.parent.parent.replace(self.parent, other)
        other.parent.balance_one_propagate()
