from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Type, cast


class IVec2[T = int]:
    def __init__(self, x: T, y: T) -> None:
        self.x: T = x
        self.y: T = y

    @staticmethod
    def splat(n: T) -> "IVec2[T]":
        return IVec2(n, n)

    @staticmethod
    def with_op(
        op: Callable[[T, T], T],
    ) -> Callable[["IVec2[T]", "T | IVec2[T]"], "IVec2[T]"]:
        return lambda self, other: IVec2(
            op(
                self.x,
                (
                    other
                    if isinstance(other, type(self))
                    else (other := type(self).splat(cast(T, other)))
                ).x,
            ),
            op(self.y, cast(IVec2[T], other).y),
        )

    def innertype(self) -> Type:
        return type(self.x)

    def __mul__(self, other: "T | IVec2[T]") -> "IVec2[T]":
        return self.with_op(self.innertype().__mul__)(self, other)

    def __add__(self, other: "T | IVec2[T]") -> "IVec2[T]":
        return self.with_op(self.innertype().__add__)(self, other)

    def __sub__(self, other: "T | IVec2[T]") -> "IVec2[T]":
        return self.with_op(self.innertype().__sub__)(self, other)

    def __floordiv__(self, other: "T| IVec2[T]") -> "IVec2[T]":
        return self.with_op(self.innertype().__floordiv__)(self, other)

    def __mod__(self, other: "T | IVec2[T]") -> "IVec2[T]":
        return self.with_op(self.innertype().__mod__)(self, other)

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, IVec2):
            return False
        return self.x == value.x and self.y == value.y

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


class Backend[T](ABC):
    """
    ABC for the maze display.
    defining how the maze should be drawn.
    """

    @abstractmethod
    def dims(self) -> IVec2:
        pass

    @abstractmethod
    def draw_tile(self, pos: IVec2) -> None:
        pass

    @abstractmethod
    def set_style(self, style: T) -> None:
        pass

    @abstractmethod
    def present(self) -> None:
        pass

    @abstractmethod
    def event(self, timeout_ms: int = -1) -> BackendEvent | None:
        pass
