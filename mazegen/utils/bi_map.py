from mazegen.utils.avl import (
    Tree as AVLTree,
    Leaf as AVLLeaf,
    NoopKey as AVLNoopKey,
)


class BiMap[K, R]:
    """
    A simple bidirectional map from elemnts to set of elements
    """

    def __init__(self) -> None:
        self.__map: dict[K, AVLTree[AVLNoopKey, R]] = {}
        self.__revmap: dict[AVLTree[AVLNoopKey, R], K] = {}
        self.__leafmap: dict[R, AVLLeaf[AVLNoopKey, R]] = {}

    def add(self, key: K, revkey: R) -> None:
        """
        Adds the given association to the map
        """
        if self.revcontains(revkey):
            self.revremove(revkey)
        if not self.contains(key):
            tree = AVLTree[AVLNoopKey, R]()
            self.__map[key] = tree
            self.__revmap[tree] = key
        self.__leafmap[revkey] = self.__map[key].append(AVLNoopKey(), revkey)

    def remove(self, key: K) -> None:
        """
        Removes the given association from the map
        """
        for revkey in self.__map[key]:
            self.__leafmap.pop(revkey)
        self.__revmap.pop(self.__map.pop(key))

    def revremove(self, revkey: R) -> None:
        """
        Removes the given reverse association from the map
        """
        leaf = self.__leafmap.pop(revkey)
        root = leaf.root()
        leaf.remove()
        if root.height() == 0:
            self.__map.pop(self.__revmap.pop(root))

    def get(self, key: K) -> AVLTree[AVLNoopKey, R]:
        """
        Gets the set of elements associated with this key
        """
        return self.__map[key] if self.contains(key) else AVLTree()

    def revget(self, revkey: R) -> K:
        """
        Gets the key associated with this element
        """
        return self.__revmap[self.__leafmap[revkey].root()]

    def key_map(self, src: K, dst: K) -> None:
        """
        Moves all elements of the source key to the destination key
        """
        if src == dst:
            return
        if src not in self.__map:
            return
        if dst not in self.__map:
            tree = AVLTree[AVLNoopKey, R]()
            self.__map[dst] = tree
            self.__revmap[tree] = dst
        self.__map[dst].rjoin(self.__map.pop(src))

    def contains(self, key: K) -> bool:
        """
        Checks whether this map contains the given key
        """
        return key in self.__map

    def revcontains(self, revkey: R) -> bool:
        """
        Checks whether this map contains the given element
        """
        return revkey in self.__leafmap
