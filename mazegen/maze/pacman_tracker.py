from collections.abc import Iterable
from mazegen.maze import Maze
from mazegen.utils import Randset, WallCoord


class PacmanTracker:
    """
    A simple tracker that keeps track of dirty cells for impass removal
    """

    def __init__(self, maze: Maze) -> None:
        self.__maze: Maze = maze
        self.__dirty: Randset[WallCoord] = Randset()
        maze.observers.add(self.__observer)

    def __repr__(self) -> str:
        return f"MazeDirtyTracker({self.__dirty})"

    def __del__(self) -> None:
        self.__maze.observers.discard(self.__observer)

    def __observer(self, wall: WallCoord) -> None:
        for cell in wall.neighbour_cells():
            for e in cell.walls():
                self.__dirty.add(e)

    def clear(self) -> Randset[WallCoord]:
        """
        Clears the current set of dirty walls and returns it
        """
        res = self.__dirty
        self.__dirty = Randset()
        return res

    def curr_dirty(self) -> Iterable[WallCoord]:
        """
        Returns an iterator over the currently dirty elements
        """
        return self.__dirty

    def end(self) -> None:
        """
        Removes this tracker's observer from the maze
        """
        self.__maze.observers.discard(self.__observer)
