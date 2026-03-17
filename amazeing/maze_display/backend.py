from collections.abc import Callable
from dataclasses import dataclass
from typing import Type, cast


class IVec2[T = int]:
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

    @staticmethod
    def with_op[T2](
        op: Callable[[T, T], T2],
    ) -> Callable[["IVec2[T]", "T | IVec2[T]"], "IVec2[T2]"]:
        return lambda self, other: IVec2(
            op(
                self.x,
                (
                    other
                    if isinstance(other, IVec2)
                    else (other := type(self).splat(other))
                ).x,
            ),
            op(self.y, cast(IVec2[T], other).y),
        )

    def innertype(self) -> Type[T]:
        return type(self.x)

    def __mul__(self, other: "T | IVec2[T]") -> "IVec2[T]":
        return self.with_op(getattr(self.innertype(), "__mul__"))(self, other)

    def __add__(self, other: "T | IVec2[T]") -> "IVec2[T]":
        return self.with_op(getattr(self.innertype(), "__add__"))(self, other)

    def __sub__(self, other: "T | IVec2[T]") -> "IVec2[T]":
        return self.with_op(getattr(self.innertype(), "__sub__"))(self, other)

    def __floordiv__(self, other: "T| IVec2[T]") -> "IVec2[T]":
        return self.with_op(getattr(self.innertype(), "__floordiv__"))(
            self, other
        )

    def __mod__(self, other: "T | IVec2[T]") -> "IVec2[T]":
        return self.with_op(getattr(self.innertype(), "__mod__"))(self, other)

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, IVec2):
            return False
        if self.x != value.x:
            return False
        if self.y != value.y:
            return False
        return True

    def __hash__(self) -> int:
        return hash((self.x, self.y))

    def xy(self) -> tuple[T, T]:
        return (self.x, self.y)

    def yx(self) -> tuple[T, T]:
        return (self.y, self.x)


@dataclass
class KeyboardInput:
    sym: str


class CloseRequested:
    pass


type BackendEvent = KeyboardInput | CloseRequested
