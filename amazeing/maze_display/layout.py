from abc import ABC, abstractmethod
from collections.abc import Callable
from sys import stderr
from .backend import IVec2


class BInt:
    def __init__(self, val: int, has_flex: bool = False) -> None:
        self.val: int = val
        self.has_flex: bool = has_flex

    def __repr__(self) -> str:
        return f"{self.val}" + (" flexible" if self.has_flex else "")

    @staticmethod
    def vector_sum(elems: list["BInt"]) -> "BInt":
        res = BInt(
            sum(map(lambda e: e.val, elems)),
            any(map(lambda e: e.has_flex, elems)),
        )
        return res

    @staticmethod
    def vector_max(elems: list["BInt"]) -> "BInt":
        res = BInt(
            max(map(lambda e: e.val, elems), default=0),
            any(map(lambda e: e.has_flex, elems)),
        )
        return res


type BVec2 = IVec2[BInt]

type Layout[T] = Callable[[list[tuple[BInt, T]], int], list[int]]


def layout_priority[T](
    sizes: list[tuple[BInt, T]], available: int
) -> list[int]:
    res = []
    for size, _ in sizes:
        size_scaled = min(size.val, available)
        res.append(size_scaled)
        available -= size_scaled
    for i, (size, _) in enumerate(sizes):
        if size.has_flex:
            res[i] += available
            break
    return res


def rdiv(a: int, b: int) -> int:
    return a // b + (a % b != 0) if a != 0 else 0


def layout_fair[T](sizes: list[tuple[BInt, T]], available: int) -> list[int]:
    res = [0 for _ in sizes]
    count = len(sizes)
    for idx, (size, _) in sorted(enumerate(sizes), key=lambda e: e[1][0].val):
        size_scaled = min(size.val, rdiv(available, count))
        res[idx] += size_scaled
        available -= size_scaled
        count -= 1
    count = sum(1 for (e, _) in sizes if e.has_flex)
    for idx, (size, _) in enumerate(sizes):
        if not size.has_flex:
            continue
        size_scaled = rdiv(available, count)
        res[idx] += size_scaled
        available -= size_scaled
        count -= 1
    return res


def layout_split[T](sized: Layout[T], flexed: Layout[T]) -> Layout[T]:
    def inner(sizes: list[tuple[BInt, T]], available: int) -> list[int]:
        flexes = [(BInt(0, e[0].has_flex), e[1]) for e in sizes]
        sizes = [(BInt(e[0].val), e[1]) for e in sizes]
        res_sizes = sized(sizes, available)
        res_flexes = flexed(flexes, available - sum(res_sizes))
        return [a + b for a, b in zip(res_sizes, res_flexes)]

    return inner


def layout_sort_shuffled[T](
    init: Layout[T], extract: Callable[[T], int]
) -> Layout[T]:
    def inner(sizes: list[tuple[BInt, T]], available: int) -> list[int]:
        mapping = [(i, extract(assoc)) for i, (_, assoc) in enumerate(sizes)]
        mapping.sort(key=lambda e: e[1])
        sizes = [e for e in sizes]
        sizes.sort(key=lambda e: extract(e[1]))
        res_init = init(sizes, available)
        res = [0 for _ in res_init]
        for src, (dst, _) in enumerate(mapping):
            res[dst] = res_init[src]
        return res

    return inner


def layout_mapped[T, U](init: Layout[T], f: Callable[[U], T]) -> Layout[U]:
    return lambda sizes, available: init(
        list(map(lambda e: (e[0], f(e[1])), sizes)), available
    )


def layout_sort_chunked[T](
    per_chunk: Layout[T],
    chunk_layout: Layout[list[tuple[BInt, T]]],
    extract: Callable[[T], int],
) -> Layout[T]:
    def layout_chunk_seq(
        sizes: list[tuple[BInt, T]], available: int
    ) -> list[int]:
        chunks: list[tuple[BInt, list[tuple[BInt, T]]]] = []
        i = 0
        curr_chunk = None

        def try_add_curr() -> None:
            nonlocal curr_chunk
            if curr_chunk is None:
                return
            chunk = curr_chunk[0]
            chunks.append(
                (
                    BInt.vector_sum([e[0] for e in chunk]),
                    chunk,
                )
            )
            curr_chunk = None

        while i < len(sizes):
            val = sizes[i]
            _, assoc = val
            extracted = extract(assoc)
            if curr_chunk is None:
                curr_chunk = ([val], extracted)
            else:
                if extracted == curr_chunk[1]:
                    curr_chunk[0].append(val)
                else:
                    try_add_curr()
                    continue
            i += 1
        try_add_curr()

        chunk_sizes = chunk_layout(chunks, available)
        res = [
            size
            for (_, chunk), chunk_layout_size in zip(chunks, chunk_sizes)
            for size in per_chunk(chunk, chunk_layout_size)
        ]
        return res

    return layout_sort_shuffled(layout_chunk_seq, extract)


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
            BInt.vector_max([e.x for e in dims]),
            BInt.vector_sum([e.y for e in dims]),
        )

    def laid_out(self, at: IVec2, into: IVec2) -> None:
        get_width: Callable[[BInt], int] = lambda w: (
            into.x if w.has_flex and w.val < into.x else min(w.val, into.x)
        )

        dims = [(box.dims(), assoc) for box, assoc in self.boxes]
        heights = self.layout([(dim.y, assoc) for dim, assoc in dims], into.y)
        widths = [(get_width(dim.x), assoc) for dim, assoc in dims]

        for height, (width, _), (box, _) in zip(heights, widths, self.boxes):
            # that copy cost me half an hour, thank you pass by reference
            # rust would have prevented that :D
            box.laid_out(at.copy(), IVec2(width, height))
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
            BInt.vector_sum([e.x for e in dims]),
            BInt.vector_max([e.y for e in dims]),
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

    def set_dims(self, dims: IVec2[BInt]) -> None:
        self.__dims = dims

    def dims(self) -> BVec2:
        return self.__dims

    def laid_out(self, at: IVec2, into: IVec2) -> None:
        self.__cb(at, into)


def vpad_box(min_pad: int = 0, cb=lambda _at, _into: None) -> FBox:
    return FBox(IVec2(BInt(0), BInt(min_pad, True)), cb)


def hpad_box(min_pad: int = 0, cb=lambda _at, _into: None) -> FBox:
    return FBox(IVec2(BInt(min_pad, True), BInt(0)), cb)


def print_cb(at: IVec2, into: IVec2) -> None:
    print(f"at {at.x, at.y}, into {into.x, into.y}")


def example() -> None:
    a = FBox(IVec2(BInt(8, False), BInt(4, False)), print_cb)
    c = HBox.noassoc(
        layout_fair,
        [
            hpad_box(),
            VBox.noassoc(layout_fair, [vpad_box(), a, vpad_box()]),
            hpad_box(),
        ],
    )
    c.laid_out(IVec2(0, 0), IVec2(3, 4))
    c.laid_out(IVec2(0, 0), IVec2(8, 30))
    c.laid_out(IVec2(0, 0), IVec2(12, 30))
