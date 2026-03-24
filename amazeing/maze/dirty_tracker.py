from collections.abc import Iterable
from amazeing.maze import Maze
from amazeing.utils import WallCoord


class DirtyTracker:
    def __init__(self, maze: Maze) -> None:
        self.__maze: Maze = maze
        self.__dirty: set[WallCoord] = set()
        maze.observers.add(self.__observer)

    def __repr__(self) -> str:
        return f"MazeDirtyTracker({self.__dirty})"

    def __del__(self) -> None:
        self.__maze.observers.discard(self.__observer)

    def __observer(self, wall: WallCoord) -> None:
        self.__dirty ^= {wall}

    def clear(self) -> set[WallCoord]:
        res = self.__dirty
        self.__dirty = set()
        return res

    def curr_dirty(self) -> Iterable[WallCoord]:
        return self.__dirty

    def end(self) -> None:
        self.__maze.observers.discard(self.__observer)
