from collections.abc import Iterable
from amazeing.maze_class.maze import Maze
from amazeing.maze_class.maze_coords import WallCoord
from amazeing.utils.randset import Randset


class MazePacmanTracker:
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
        res = self.__dirty
        self.__dirty = Randset()
        return res

    def curr_dirty(self) -> Iterable[WallCoord]:
        return self.__dirty

    def end(self) -> None:
        self.__maze.observers.discard(self.__observer)
