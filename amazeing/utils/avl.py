from collections.abc import Callable
from typing import cast
import textwrap


class Tree[T]:
    def __init__(self) -> None:
        self.root: Node[T] | None = None

    def __repr__(self) -> str:
        return f"{self.root}" if self.root is not None else "(empty)"

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
        return cast(Leaf, self.root.rhs)

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

    def join(self, rhs: "Tree[T]") -> None:
        if self.height() >= rhs.height():
            self.rjoin(rhs)
        else:
            rhs.ljoin(self)
            self.exchange(rhs)

    def ljoin(self, lhs: "Tree[T]") -> None:
        if self.root is None:
            self.exchange(lhs)
        if self.root is None or lhs.root is None:
            return
        curr = self.root
        insert = lhs.root
        lhs.root = None
        while isinstance(curr, Branch) and curr.height > insert.height + 1:
            curr = curr.lhs
        parent = curr.parent
        new = Branch(curr.parent, insert.with_parent, curr.with_parent)
        parent.replace(curr, new)
        new.update_height()
        new.parent.balance_one_propagate()

    def rjoin(self, rhs: "Tree[T]") -> None:
        if self.root is None:
            self.exchange(rhs)
        if self.root is None or rhs.root is None:
            return
        curr = self.root
        insert = rhs.root
        rhs.root = None
        while isinstance(curr, Branch) and curr.height > insert.height + 1:
            curr = curr.lhs
        parent = curr.parent
        new = Branch(curr.parent, curr.with_parent, insert.with_parent)
        parent.replace(curr, new)
        new.update_height()
        new.parent.balance_one_propagate()


class Node[T]:
    def __init__(self, parent: "Branch[T] | Tree[T]") -> None:
        self.parent: Branch[T] | Tree[T] = parent
        self.height: int = 1

    def with_parent(self, parent: "Branch[T] | Tree[T]") -> "Node[T]":
        self.parent = parent
        return self

    def root(self) -> Tree[T]:
        if isinstance(self.parent, Tree):
            return self.parent
        return self.parent.root()


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
        #   self     -->     self
        #  /    \           /    \
        # a      n         n      c
        #       / \       / \
        #      b   c     a   b
        n = self.rhs
        if not isinstance(n, Branch):
            return
        a = self.lhs
        b = n.lhs
        c = n.rhs
        n.lhs = a
        n.rhs = b
        self.rhs = c
        self.lhs = n
        a.parent = n
        b.parent = n
        c.parent = self
        n.parent = self
        n.update_height()
        self.update_height()

    def rotate_ll(self) -> None:
        # Simple AVL rotate:
        #
        #     self   -->    self
        #    /    \        /    \
        #   n      c     a       n
        #  / \                  / \
        # a   b                b   c
        n = self.lhs
        if not isinstance(n, Branch):
            return
        a = n.lhs
        b = n.rhs
        c = self.rhs
        self.lhs = a
        n.lhs = b
        n.rhs = c
        self.rhs = n
        a.parent = self
        b.parent = n
        c.parent = n
        n.parent = self
        n.update_height()
        self.update_height()

    def rotate_rl(self) -> None:
        # Double AVL rotate:
        #
        #   self     -->     self
        #  /    \           /    \
        # a      n         n      m
        #       / \       / \    / \
        #      m   d     a   b  c   d
        #     / \
        #    b   c
        n = self.lhs
        if not isinstance(n, Branch):
            return
        m = n.lhs
        if not isinstance(m, Branch):
            return
        a = self.lhs
        b = m.lhs
        c = m.rhs
        d = n.rhs
        n.lhs = a
        n.rhs = b
        m.lhs = c
        m.rhs = d
        self.lhs = n
        self.rhs = m
        a.parent = n
        b.parent = n
        c.parent = m
        d.parent = m
        n.parent = self
        m.parent = self
        n.update_height()
        m.update_height()
        self.update_height()

    def rotate_lr(self) -> None:
        # Double AVL rotate:
        #
        #     self   -->     self
        #    /    \         /    \
        #   n      d       n      m
        #  / \            / \    / \
        # a   m          a   b  c   d
        #    / \
        #   b   c
        n = self.lhs
        if not isinstance(n, Branch):
            return
        m = n.rhs
        if not isinstance(m, Branch):
            return
        a = n.lhs
        b = m.lhs
        c = m.rhs
        d = self.rhs
        n.lhs = a
        n.rhs = b
        m.lhs = c
        m.rhs = d
        self.lhs = n
        self.rhs = m
        a.parent = n
        b.parent = n
        c.parent = m
        d.parent = m
        n.parent = self
        m.parent = self
        n.update_height()
        m.update_height()
        self.update_height()

    def append(self, value: T) -> "Leaf[T]":
        if self.rhs is None:
            leaf = Leaf[T](self, value)
            self.rhs = leaf
            self.balance_one_propagate()
            return leaf
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

    def balance_one(self):
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

    def __repr__(self) -> str:
        return f"leaf: {self.value}"

    def remove(self) -> None:
        if isinstance(self.parent, Tree):
            self.parent.root = None
            return
        other = self.parent.get_other(self)
        self.parent.parent.replace(self.parent, other)
        other.parent.balance_one_propagate()
