from .avl import Tree as AVLTree, Leaf as AVLLeaf


class BiMap[K, R]:
    def __init__(self) -> None:
        self.__map: dict[K, AVLTree[R]] = {}
        self.__revmap: dict[AVLTree[R], K] = {}
        self.__leafmap: dict[R, AVLLeaf[R]] = {}

    def add(self, key: K, revkey: R) -> None:
        if self.revcontains(revkey):
            self.revremove(revkey)
        if not self.contains(key):
            tree = AVLTree[R]()
            self.__map[key] = tree
            self.__revmap[tree] = key
        self.__leafmap[revkey] = self.__map[key].append(revkey)

    def remove(self, key: K) -> None:
        for revkey in self.__map[key]:
            self.__leafmap.pop(revkey)
        self.__revmap.pop(self.__map.pop(key))

    def revremove(self, revkey: R) -> None:
        leaf = self.__leafmap.pop(revkey)
        root = leaf.root()
        leaf.remove()
        if root.height() == 0:
            self.__map.pop(self.__revmap.pop(root))

    def get(self, key: K) -> AVLTree[R]:
        return self.__map[key] if self.contains(key) else AVLTree()

    def revget(self, revkey: R) -> K:
        return self.__revmap[self.__leafmap[revkey].root()]

    def key_map(self, src: K, dst: K) -> None:
        if src == dst:
            return
        if src not in self.__map:
            return
        if dst not in self.__map:
            tree = AVLTree[R]()
            self.__map[dst] = tree
            self.__revmap[tree] = dst
        self.__map[dst].rjoin(self.__map.pop(src))

    def contains(self, key: K) -> bool:
        return key in self.__map

    def revcontains(self, revkey: R) -> bool:
        return revkey in self.__leafmap
