from mazegen.maze import Maze
from mazegen.utils import WallCoord


class DirtyTracker:
    """
    A simple tracker that keeps track of which walls were changed
    """

    def __init__(self, maze: Maze) -> None:
        self.__maze: Maze = maze
        self.__dirty: set[WallCoord] = set()
        maze.observers.add(self.__observer)

    def __repr__(self) -> str:
        return f"MazeDirtyTracker({self.__dirty})"

    def __observer(self, wall: WallCoord) -> None:
        self.__dirty ^= {wall}

    def clear(self) -> set[WallCoord]:
        """
        Returns the currently dirty set of walls and resets it
        """
        res = self.__dirty
        self.__dirty = set()
        return res

    def curr_dirty(self) -> set[WallCoord]:
        """
        Returns the currently dirty set of walls, which may be modified
        if a wall is later changed
        """
        return self.__dirty

    def end(self) -> None:
        """
        Remove this tracker from the observers of the maze
        """
        self.__maze.observers.discard(self.__observer)
