from amazeing.maze_class.maze import Maze
from amazeing.maze_class.maze_coords import CellCoord, WallCoord
from amazeing.utils import BiMap
from amazeing.utils import AVLTree, AVLLeaf


class NetworkID:
    pass


class DualForest[T]:
    """
    A forest of trees that contour networks
    AVL trees are used to represent the contours, such that split and
    merge operations are of complexity O(log n), each tree is a cycle
    of each connex graph boundary
    """

    def __init__(
        self,
    ) -> None:
        self.__trees: set[AVLTree[T]] = set()
        self.__revmap: dict[T, set[AVLLeaf[T]]] = {}


class MazeNetworkTracker:
    def __init__(self, maze: Maze) -> None:
        self.__maze: Maze = maze
        self.__networks_wall: BiMap[NetworkID, WallCoord] = BiMap()
        self.__networks_cell: BiMap[NetworkID, CellCoord] = BiMap()

        netid = NetworkID()
        for cell in maze.all_cells():
            self.__networks_cell.add(netid, cell)

        maze.observers.add(self.__observer)
        for wall in maze.walls_full():
            self.__observer(wall)

    def __observer(self, wall: WallCoord) -> None:
        return

    def end(self):
        self.__maze.observers.discard(self.__observer)
