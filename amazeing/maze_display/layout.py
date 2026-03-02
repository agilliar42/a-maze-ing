from abc import ABC, abstractmethod
from collections.abc import Callable
from .backend import IVec2


class BInt:
    def __init__(self, val: int, has_flex: bool = False) -> None:
        self.val: int = val
        self.has_flex: bool = has_flex


type BVec2 = IVec2[BInt]

type Layout[T] = Callable[[list[tuple[BInt, T]], int], list[int]]


def layout_priority(sizes: list[BInt], available: int) -> list[int]:
    res = []
    for size in sizes:
        size_scaled = min(size.val, available)
        res.append(size_scaled)
        available -= size_scaled
    return res


def rdiv(a: int, b: int) -> int:
    return a // b + (a % b != 0) if a != 0 else 0


def layout_fair[T](sizes: list[tuple[BInt, T]], available: int) -> list[int]:
    res = [0 for _ in sizes]
    count = len(sizes)
    for idx, size in sorted(enumerate(sizes), key=lambda e: e[1][0].val):
        size_scaled = min(size[0].val, rdiv(available, count))
        res[idx] += size_scaled
        available -= size_scaled
        count -= 1
    count = sum(1 for e in sizes if e[0].has_flex)
    for idx, size in enumerate(sizes):
        if not size[0].has_flex:
            continue
        size_scaled = rdiv(available, count)
        res[idx] += size_scaled
        available -= size_scaled
        count -= 1
    return res


class Box(ABC):
    @abstractmethod
    def dims(self) -> BVec2: ...
    @abstractmethod
    def laid_out(self, at: IVec2, into: IVec2) -> None: ...


class VBox[T](Box):
    def __init__(
        self, layout: Layout, boxes: list[tuple[Box, T]] = []
    ) -> None:
        self.boxes: list[tuple[Box, T]] = boxes
        self.layout: Layout = layout

    @staticmethod
    def noassoc(layout: Layout, boxes: list[Box]) -> "VBox[None]":
        return VBox(layout, [(box, None) for box in boxes])

    def dims(self) -> BVec2:
        dims = [box.dims() for box, _ in self.boxes]
        return IVec2(
            BInt(
                max(map(lambda e: e.x.val, dims)),
                any(map(lambda e: e.x.has_flex, dims)),
            ),
            BInt(
                sum(map(lambda e: e.y.val, dims)),
                any(map(lambda e: e.y.has_flex, dims)),
            ),
        )

    def laid_out(self, at: IVec2, into: IVec2) -> None:
        get_width: Callable[[BInt], int] = lambda w: (
            into.x if w.has_flex and w.val < into.x else min(w.val, into.x)
        )

        dims = [(box.dims(), assoc) for box, assoc in self.boxes]
        heights = self.layout([(dim.y, assoc) for dim, assoc in dims], into.y)
        widths = [(get_width(dim.x), assoc) for dim, assoc in dims]

        for height, (width, _), (box, _) in zip(heights, widths, self.boxes):
            box.laid_out(at, IVec2(width, height))
            at.y += height


class HBox[T](Box):
    def __init__(
        self, layout: Layout, boxes: list[tuple[Box, T]] = []
    ) -> None:
        self.boxes: list[tuple[Box, T]] = boxes
        self.layout: Layout = layout

    @staticmethod
    def noassoc(layout: Layout, boxes: list[Box]) -> "HBox[None]":
        return HBox(layout, [(box, None) for box in boxes])

    def dims(self) -> BVec2:
        dims = [box.dims() for box, _ in self.boxes]
        return IVec2(
            BInt(
                sum(map(lambda e: e.x.val, dims)),
                any(map(lambda e: e.x.has_flex, dims)),
            ),
            BInt(
                max(map(lambda e: e.y.val, dims)),
                any(map(lambda e: e.y.has_flex, dims)),
            ),
        )

    def laid_out(self, at: IVec2, into: IVec2) -> None:
        get_height: Callable[[BInt], int] = lambda w: (
            into.y if w.has_flex and w.val < into.y else min(w.val, into.y)
        )

        dims = [(box.dims(), assoc) for box, assoc in self.boxes]
        widths = self.layout([(dim.x, assoc) for dim, assoc in dims], into.x)
        heights = [(get_height(dim.y), assoc) for dim, assoc in dims]

        for (height, _), width, (box, _) in zip(heights, widths, self.boxes):
            box.laid_out(at, IVec2(width, height))
            at.x += width


class FBox(Box):
    def __init__(
        self, dims: BVec2, cb: Callable[[IVec2, IVec2], None]
    ) -> None:
        self.__dims: BVec2 = dims
        self.__cb: Callable[[IVec2, IVec2], None] = cb

    def dims(self) -> BVec2:
        return self.__dims

    def laid_out(self, at: IVec2, into: IVec2) -> None:
        self.__cb(at, into)


def vpad_box[T](min_pad: int = 0) -> FBox:
    return FBox(IVec2(BInt(0), BInt(min_pad, True)), lambda _at, _into: None)


def hpad_box(min_pad: int = 0) -> FBox:
    return FBox(IVec2(BInt(min_pad, True), BInt(0)), lambda _at, _into: None)


def print_cb(at: IVec2, into: IVec2) -> None:
    print(f"at {at.x, at.y}, into {into.x, into.y}")


def example() -> None:
    a = FBox(IVec2(BInt(8, False), BInt(4, True)), print_cb)
    b = FBox(IVec2(BInt(4, False), BInt(8, False)), print_cb)
    c = VBox.noassoc(layout_fair, [a, b])
    c.laid_out(IVec2(0, 0), IVec2(3, 4))
    c.laid_out(IVec2(0, 0), IVec2(8, 30))
    c.laid_out(IVec2(0, 0), IVec2(12, 30))
