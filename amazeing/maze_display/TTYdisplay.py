from sys import stderr
from .backend import Backend, IVec2, BackendEvent, KeyboardInput
import curses


class TTYTile:
    def __init__(self, pixels: list[list[tuple[str, int]]]) -> None:
        self.__pixels: list[list[tuple[str, int]]] = pixels

    def blit(
        self, src: IVec2, dst: IVec2, size: IVec2, window: curses.window
    ) -> None:
        for y, line in enumerate(self.__pixels[src.y : src.y + size.y]):
            for x, (char, attrs) in enumerate(line[src.x : src.x + size.x]):
                window.addch(dst.y + y, dst.x + x, char, attrs)


class TTYTileMap:
    def __init__(self, wall_dim: IVec2, cell_dim: IVec2) -> None:
        self.__wall_dim: IVec2 = wall_dim
        self.__cell_dim: IVec2 = cell_dim
        self.__tiles: list[TTYTile] = []

    def add_tile(self, tile: TTYTile) -> int:
        res = len(self.__tiles)
        self.__tiles.append(tile)
        return res

    def dst_coord(self, pos: IVec2) -> IVec2:
        return (n := pos // 2) * self.__cell_dim + (pos - n) * self.__wall_dim

    def src_coord(self, pos: IVec2) -> IVec2:
        return pos % 2 * self.__wall_dim

    def tile_size(self, pos: IVec2) -> IVec2:
        return (pos + 1) % 2 * self.__wall_dim + pos % 2 * self.__cell_dim

    def draw_at(self, pos: IVec2, idx: int, window: curses.window) -> None:
        self.__tiles[idx].blit(
            self.src_coord(pos),
            self.dst_coord(pos),
            self.tile_size(pos),
            window,
        )


class TTYBackend(Backend[int]):
    """
    Takes the ABC Backend and displays the maze in the terminal.
    """

    def __init__(
        self, maze_dims: IVec2, wall_dim: IVec2, cell_dim: IVec2
    ) -> None:
        super().__init__()
        self.__tilemap: TTYTileMap = TTYTileMap(wall_dim, cell_dim)
        self.__style = 0

        dims = self.__tilemap.dst_coord(maze_dims * 2 + 2)

        self.__screen: curses.window = curses.initscr()
        curses.start_color()
        curses.noecho()
        curses.cbreak()
        self.__screen.keypad(True)

        self.__pad: curses.window = curses.newpad(dims.y, dims.x)
        self.__dims = maze_dims

    def __del__(self):
        curses.nocbreak()
        self.__screen.keypad(False)
        curses.echo()
        curses.endwin()

    def add_style(self, style: TTYTile) -> int:
        return self.__tilemap.add_tile(style)

    def dims(self) -> IVec2:
        return self.__dims

    def draw_tile(self, pos: IVec2) -> None:
        self.__tilemap.draw_at(pos, self.__style, self.__pad)

    def set_style(self, style: int) -> None:
        self.__style = style

    def present(self) -> None:
        self.__screen.refresh()
        self.__pad.refresh(
            0,
            0,
            0,
            0,
            min(self.__pad.getmaxyx()[0] - 1, self.__screen.getmaxyx()[0] - 1),
            min(self.__pad.getmaxyx()[1] - 1, self.__screen.getmaxyx()[1] - 1),
        )

    def event(self, timeout_ms: int = -1) -> BackendEvent | None:
        self.__screen.timeout(timeout_ms)
        try:
            return KeyboardInput(self.__screen.getkey())
        except curses.error:
            return None
