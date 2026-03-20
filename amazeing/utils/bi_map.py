from collections.abc import Iterable


class BiMap[K, R]:
    def __init__(self) -> None:
        self.__map: dict[K, set[R]] = {}
        self.__revmap: dict[R, K] = {}

    def add(self, key: K, revkey: R) -> None:
        if self.revcontains(revkey):
            self.revremove(revkey)
        if not self.contains(key):
            self.__map[key] = set()
        self.__revmap[revkey] = key
        self.__map[key].add(revkey)

    def remove(self, key: K) -> None:
        for revkey in self.__map[key]:
            self.__revmap.pop(revkey)
        self.__map.pop(key)

    def revremove(self, revkey: R) -> None:
        key = self.__revmap.pop(revkey)
        self.__map[key].remove(revkey)
        if len(self.__map[key]) == 0:
            self.__map.pop(key)

    def get(self, key: K) -> set[R]:
        return self.__map[key] if self.contains(key) else set()

    def revget(self, revkey: R) -> K:
        return self.__revmap[revkey]

    def contains(self, key: K) -> bool:
        return key in self.__map

    def revcontains(self, revkey: R) -> bool:
        return revkey in self.__revmap
