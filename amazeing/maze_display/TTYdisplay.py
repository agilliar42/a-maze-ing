from sys import stderr
from amazeing.maze_display.layout import (
    BInt,
    Box,
    FBox,
    HBox,
    VBox,
    layout_fair,
    vpad_box,
    hpad_box,
)
from .backend import Backend, IVec2, BackendEvent, KeyboardInput
import curses


class TTYTile:
    def __init__(self, pixels: list[list[tuple[str, int]]]) -> None:
        self.__pixels: list[list[tuple[str, int]]] = pixels

    def blit(
        self, src: IVec2, dst: IVec2, size: IVec2, window: curses.window
    ) -> None:
        for y, line in enumerate(
            self.__pixels[src.y : src.y + size.y]  # noqa E203
        ):
            for x, (char, attrs) in enumerate(
                line[src.x : src.x + size.x]  # noqa E203
            ):
                try:
                    window.addch(dst.y + y, dst.x + x, char, attrs)
                except curses.error:
                    pass  # dumb exception when writing bottom right corner


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


class ScrollablePad:
    def __init__(
        self,
        dims: IVec2,
        constrained: bool = True,
        init_pos: IVec2 = IVec2.splat(0),
    ) -> None:
        self.__pos = init_pos
        self.pad: curses.window = curses.newpad(dims.y, dims.x)
        self.constrained = constrained

    def dims(self) -> IVec2:
        y, x = self.pad.getmaxyx()
        return IVec2(x, y)

    def clamp(self, dims: IVec2) -> None:
        self.__pos = IVec2.with_op(min)(
            IVec2.with_op(max)(self.__pos, dims - self.dims()), IVec2.splat(0)
        )

    def refresh(self, at: IVec2, into: IVec2) -> None:
        if self.constrained:
            self.clamp(into)

        pad_start = IVec2.with_op(max)(
            IVec2.splat(0) - self.__pos, IVec2.splat(0)
        )
        win_start = IVec2.with_op(max)(self.__pos, IVec2.splat(0))
        draw_dim = IVec2.with_op(min)(
            self.dims() - pad_start, into - win_start
        )
        if draw_dim.x <= 0 or draw_dim.y <= 0:
            return
        draw_start = at + win_start
        draw_end = draw_start + draw_dim - IVec2.splat(1)
        self.pad.refresh(
            *pad_start.yx(),
            *draw_start.yx(),
            *draw_end.yx(),
        )

    def move(self, by: IVec2) -> None:
        self.__pos = self.__pos + by

    def scroll(self, by: IVec2) -> None:
        self.move(by * IVec2.splat(-1))


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

        dims = self.__tilemap.dst_coord(maze_dims * 2 + 1)

        self.__screen: curses.window = curses.initscr()
        curses.start_color()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)
        self.__screen.keypad(True)

        self.__pad: ScrollablePad = ScrollablePad(dims)
        self.__dims = maze_dims

        maze_box = FBox(
            IVec2(BInt(dims.x), BInt(dims.y)),
            self.__pad.refresh,
        )
        self.__layout: Box = VBox.noassoc(
            layout_fair,
            [
                vpad_box(),
                HBox.noassoc(layout_fair, [hpad_box(), maze_box, hpad_box()]),
                vpad_box(),
            ],
        )

    def __del__(self):
        curses.curs_set(1)
        curses.nocbreak()
        self.__screen.keypad(False)
        curses.echo()
        curses.endwin()

    def add_style(self, style: TTYTile) -> int:
        return self.__tilemap.add_tile(style)

    def dims(self) -> IVec2:
        return self.__dims

    def draw_tile(self, pos: IVec2) -> None:
        self.__tilemap.draw_at(pos, self.__style, self.__pad.pad)

    def set_style(self, style: int) -> None:
        self.__style = style

    def present(self) -> None:
        self.__screen.erase()
        self.__screen.refresh()
        y, x = self.__screen.getmaxyx()
        self.__layout.laid_out(IVec2(0, 0), IVec2(x, y))

    def event(self, timeout_ms: int = -1) -> BackendEvent | None:
        self.__screen.timeout(timeout_ms)
        try:
            key = self.__screen.getkey()
        except curses.error:
            return None
        match key:
            case "KEY_RESIZE":
                pass
            case "KEY_DOWN":
                self.__pad.scroll(IVec2(0, 1))
            case "KEY_UP":
                self.__pad.scroll(IVec2(0, -1))
            case "KEY_RIGHT":
                self.__pad.scroll(IVec2(1, 0))
            case "KEY_LEFT":
                self.__pad.scroll(IVec2(-1, 0))
            case _:
                return KeyboardInput(key)
        self.present()
