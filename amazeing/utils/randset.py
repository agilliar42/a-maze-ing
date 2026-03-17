from collections.abc import Iterable, MutableSequence, MutableSet
from typing import cast, overload


class Randset[T](MutableSequence[T], MutableSet[T]):
    def __init__(self) -> None:
        self.__elems: list[T] = []
        self.__idx_map: dict[T, int] = {}

    def __repr__(self) -> str:
        return str(self.__idx_map)

    @overload
    def __getitem__(self, pos: int) -> T: ...
    @overload
    def __getitem__(self, pos: slice) -> "Randset[T]": ...

    def __getitem__(self, pos: int | slice) -> T | "Randset[T]":
        if isinstance(pos, int):
            return self.__elems[pos]
        else:
            res = Randset[T]()
            res.__elems = self.__elems[pos]
            res.__idx_map = {e: i for i, e in enumerate(res.__elems)}
            return res

    @overload
    def __setitem__(self, pos: int, value: T) -> None: ...
    @overload
    def __setitem__(self, pos: slice, value: Iterable[T]) -> None: ...

    def __setitem__(self, pos: int | slice, value: T | Iterable[T]) -> None:
        if isinstance(pos, int):
            del self.__idx_map[self.__elems[pos]]
            self.__elems[pos] = cast(T, value)
            self.__idx_map[cast(T, value)] = pos
        else:
            raise NotImplementedError("slice setitem in randset")

    def __len__(self) -> int:
        return len(self.__elems)

    @overload
    def __delitem__(self, pos: int) -> None: ...

    @overload
    def __delitem__(self, pos: slice) -> None: ...

    def __delitem__(self, pos: int | slice) -> None:
        if isinstance(pos, int):
            self.discard(self.__elems[pos])
        else:
            elems = self.__elems[pos]
            for e in elems:
                self.discard(e)

    def add(self, value: T) -> None:
        if value in self.__idx_map:
            return
        self.__idx_map[value] = len(self.__elems)
        self.__elems.append(value)

    def discard(self, value: T) -> None:
        if value not in self.__idx_map:
            return
        self.__idx_map[self.__elems[-1]] = self.__idx_map[value]
        self.__elems[self.__idx_map[value]] = self.__elems[-1]
        self.__elems.pop()
        del self.__idx_map[value]

    def insert(self, index: int, value: T) -> None:
        raise NotImplementedError("index insert randset")
