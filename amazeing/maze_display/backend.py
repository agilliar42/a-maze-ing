from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass


class IVec2:
    def __init__(self, x: int, y: int) -> None:
        self.x: int = x
        self.y: int = y

    @staticmethod
    def splat(n: int) -> "IVec2":
        return IVec2(n, n)

    @staticmethod
    def with_op(
        op: Callable[[int, int], int],
    ) -> Callable[["IVec2", "int | IVec2"], "IVec2"]:
        return lambda self, other: IVec2(
            op(
                self.x,
                (
                    other
                    if isinstance(other, IVec2)
                    else (other := IVec2.splat(other))
                ).x,
            ),
            op(self.y, other.y),
        )

    def __mul__(self, other: "int | IVec2") -> "IVec2":
        return self.with_op(int.__mul__)(self, other)

    def __add__(self, other: "int | IVec2") -> "IVec2":
        return self.with_op(int.__add__)(self, other)

    def __sub__(self, other: "int | IVec2") -> "IVec2":
        return self.with_op(int.__sub__)(self, other)

    def __floordiv__(self, other: "int | IVec2") -> "IVec2":
        return self.with_op(int.__floordiv__)(self, other)

    def __mod__(self, other: "int | IVec2") -> "IVec2":
        return self.with_op(int.__mod__)(self, other)


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
