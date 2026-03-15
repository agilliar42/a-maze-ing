from collections.abc import Iterable
from amazeing.maze_class.maze import Maze
from amazeing.maze_class.maze_coords import WallCoord


class MazeDirtyTracker:
    def __init__(self, maze: Maze) -> None:
        self.__maze: Maze = maze
        self.__dirty: set[WallCoord] = set()
        maze.observers.add(self.__observer)

    def __del__(self):
        self.__maze.observers.discard(self.__observer)

    def __observer(self, wall: WallCoord) -> None:
        self.__dirty ^= {wall}

    def end(self):
        self.__maze.observers.discard(self.__observer)

    def clear(self) -> set[WallCoord]:
        res = self.__dirty
        self.__dirty = set()
        return res

    def curr_dirty(self) -> Iterable[WallCoord]:
        return list(self.__dirty)
