from collections.abc import Callable
from typing import Type


class IVec2[T = int]:
    __slots__: tuple[str, str] = ("x", "y")

    def copy(self, inner_copy: Callable[[T], T] = lambda e: e) -> "IVec2[T]":
        return IVec2(inner_copy(self.x), inner_copy(self.y))

    def __init__(self, x: T, y: T) -> None:
        self.x: T = x
        self.y: T = y

    @staticmethod
    def splat(n: T) -> "IVec2[T]":
        return IVec2(n, n)

    def __repr__(self) -> str:
        return f"{self.x, self.y}"

    def with_op[T2](
        self, op: Callable[[T, T], T2], other: "IVec2[T]"
    ) -> "IVec2[T2]":
        return IVec2(
            op(self.x, other.x),
            op(self.y, other.y),
        )

    def innertype(self) -> Type[T]:
        return type(self.x)

    def __mul__(self, other: "IVec2[T]") -> "IVec2[T]":
        return IVec2(self.x * other.x, self.y * other.y)  # type:ignore

    def __add__(self, other: "IVec2[T]") -> "IVec2[T]":
        return IVec2(self.x + other.x, self.y + other.y)  # type:ignore

    def __sub__(self, other: "IVec2[T]") -> "IVec2[T]":
        return IVec2(self.x - other.x, self.y - other.y)  # type:ignore

    def __floordiv__(self, other: "IVec2[T]") -> "IVec2[T]":
        return IVec2(self.x // other.x, self.y // other.y)  # type:ignore

    def __mod__(self, other: "IVec2[T]") -> "IVec2[T]":
        return IVec2(self.x % other.x, self.y % other.y)  # type:ignore

    def __eq__(self, value: object, /) -> bool:
        return (
            isinstance(value, IVec2)
            and self.x == value.x
            and self.y == value.y
        )

    def __hash__(self) -> int:
        return hash((self.x, self.y))

    def lane_min(self, other: "IVec2[T]") -> "IVec2[T]":
        return IVec2(min(self.x, other.x), min(self.y, other.y))  # type:ignore

    def lane_max(self, other: "IVec2[T]") -> "IVec2[T]":
        return IVec2(max(self.x, other.x), max(self.y, other.y))  # type:ignore

    def xy(self) -> tuple[T, T]:
        return (self.x, self.y)

    def yx(self) -> tuple[T, T]:
        return (self.y, self.x)
