from .backend import Backend, PixelCoord
import sys


class TTYBackend(Backend):
    """
    Takes the ABC Backend and displays the maze in the terminal.
    """
    def __init__(
        self, maze_width: int, maze_height: int, style: str = " "
    ) -> None:
        super().__init__()
        self.width: int = maze_width * 2 + 1
        self.height: int = maze_height * 2 + 1
        self.style: str = style
        self.lines: list[list[str]] = [
            [style for _ in range(0, self.width)]
            for _ in range(0, self.height)
        ]

    def draw_pixel(self, pos: PixelCoord) -> None:
        self.lines[pos.y][pos.x] = self.style

    def set_style(self, style: str) -> None:
        self.style = style

    def present(self) -> None:
        for line in self.lines:
            for char in line:
                sys.stdout.write(char)
            sys.stdout.write("\n")
        sys.stdout.flush()
