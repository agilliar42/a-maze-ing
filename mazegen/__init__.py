__version__ = "1.0.0"
__author__ = "luflores & agilliar"


class MazeGenerator:
    """
    A very simple but not very practical maze generator
    The options have the same effect as in the config file
    """

    def __init__(
        self,
        dims: tuple[int, int],
        entry: tuple[int, int],
        exit: tuple[int, int],
        perfect: bool = True,
        seed: int | None = None,
    ) -> None:
        from mazegen.maze import (
            Maze,
            Pattern,
            make_perfect,
            make_pacman,
            NetworkTracker,
            PacmanTracker,
        )
        from mazegen.utils import IVec2
        import random

        prev_rand = random.getstate()
        random.seed(seed)

        maze = Maze(IVec2(*dims), IVec2(*entry), IVec2(*exit))
        maze.outline()
        Pattern(Pattern.FT_PATTERN).centered_for(
            maze.dims, {maze.entry, maze.exit}
        ).write_to_maze(maze)
        walls_const = set(maze.walls_full())

        make_perfect(maze, NetworkTracker(maze))
        if not perfect:
            make_pacman(maze, walls_const, PacmanTracker(maze))

        random.setstate(prev_rand)
        self.__maze = maze

    def get_output(self) -> str:
        """
        Returns the output as formatted for the output file
        """
        from mazegen.maze.output import format_output

        return format_output(self.__maze)


__all__ = ["MazeGenerator"]
