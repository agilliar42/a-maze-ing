from abc import ABC, abstractmethod
from collections.abc import Callable, Generator, Iterable
from amazeing.utils import BiMap
from amazeing.config.config_parser import Color, Config, ColoredLine, ColorPair
from amazeing.maze_display.layout import (
    BInt,
    Box,
    DBox,
    FBox,
    HBox,
    VBox,
    layout_fair,
    layout_priority,
    layout_sort_chunked,
    layout_split,
)
from .backend import IVec2, BackendEvent, KeyboardInput
import curses


class BackendException(Exception):
    pass


class ITile(ABC):
    @abstractmethod
    def size(self) -> IVec2: ...
    @abstractmethod
    def pos(self) -> IVec2: ...

    def __init__(self, pad: curses.window) -> None:
        super().__init__()
        self.pad: curses.window = pad

    def blit(
        self, src: IVec2, dst: IVec2, size: IVec2, window: curses.window
    ) -> None:
        if size.x <= 0 or size.y <= 0:
            return

        self.pad.overwrite(
            window,
            *(src + self.pos()).yx(),
            *dst.yx(),
            *(dst + size - IVec2.splat(1)).yx(),
        )

    def blit_iter(
        self, src: IVec2, dst: IVec2, size: IVec2
    ) -> Generator[tuple[IVec2, "SubPixel"]]:
        for y in range(size.y):
            for x in range(size.x):
                pos = IVec2(x, y)
                yield (dst + pos, SubPixel(self, src + pos))

    def blit_wrapping_subtiles(
        self,
        src: IVec2,
        dst: IVec2,
        size: IVec2,
        justify: IVec2,
    ) -> Generator[tuple[IVec2, "SubTile"]]:
        def size_offset_iter(
            start: int, size: int, mod: int
        ) -> Generator[tuple[int, int]]:
            pos = 0
            while pos < size:
                step = min(mod - (start + pos) % mod, size - pos)
                yield (step, pos)
                pos += step

        if size.x <= 0 or size.y <= 0:
            return
        dims = self.size()
        justify_offset = dims - (src + size) % dims
        src = src + justify_offset * justify
        src = src % dims
        for x_size, x_offset in size_offset_iter(src.x, size.x, dims.x):
            for y_size, y_offset in size_offset_iter(src.y, size.y, dims.y):
                sub_size = IVec2(x_size, y_size)
                offset = IVec2(x_offset, y_offset)
                yield (
                    dst + offset,
                    SubTile(self, (src + offset) % dims, sub_size),
                )

    def blit_wrapping(
        self,
        src: IVec2,
        dst: IVec2,
        size: IVec2,
        window: curses.window,
        justify: IVec2 = IVec2.splat(0),
    ) -> None:
        for pos, subtile in self.blit_wrapping_subtiles(
            src, dst, size, justify
        ):
            subtile.blit(IVec2.splat(0), pos, subtile.size(), window)

    def blit_wrapping_iter(
        self,
        src: IVec2,
        dst: IVec2,
        size: IVec2,
        justify: IVec2 = IVec2.splat(0),
    ) -> Generator[tuple[IVec2, "SubPixel"]]:
        for pos, subtile in self.blit_wrapping_subtiles(
            src, dst, size, justify
        ):
            for e in subtile.blit_iter(IVec2.splat(0), pos, subtile.size()):
                yield e


class Tile(ITile):
    def __init__(
        self, pixels: list[list[tuple[str, int]]], dims: IVec2
    ) -> None:
        def pad_write_safe(
            pad: curses.window, dst: IVec2, char: str, attrs: int
        ) -> None:
            try:
                pad.addch(dst.y, dst.x, char, attrs)
            except curses.error:
                pass  # dumb exception when writing bottom right corner

        if (
            len(pixels) > dims.y
            or max(
                map(lambda line: sum(map(lambda s: len(s[0]), line)), pixels)
            )
            > dims.x
        ):
            raise BackendException("Tile too big to fit in set dimensions")

        super().__init__(curses.newpad(*dims.yx()))

        for y, line in enumerate(pixels):
            x = 0
            for s, attrs in line:
                for char in s:
                    pad_write_safe(self.pad, IVec2(x, y), char, attrs)
                    x += 1

    def size(self) -> IVec2:
        y, x = self.pad.getmaxyx()
        return IVec2(x, y)

    def pos(self) -> IVec2:
        return IVec2.splat(0)


class SubPixel(ITile):
    def __init__(self, tile: ITile, pos: IVec2) -> None:
        super().__init__(tile.pad)
        self.__pos: IVec2 = tile.pos() + pos

    def size(self) -> IVec2:
        return IVec2.splat(1)

    def pos(self) -> IVec2:
        return self.__pos


class SubTile(ITile):
    def __init__(self, tile: ITile, pos: IVec2, size: IVec2) -> None:
        super().__init__(tile.pad)
        self.__pos: IVec2 = tile.pos() + pos
        self.__size: IVec2 = size

    def size(self) -> IVec2:
        return self.__size

    def pos(self) -> IVec2:
        return self.__pos


class MazeTileMap:
    def __init__(self, wall_dim: IVec2, cell_dim: IVec2) -> None:
        self.__wall_dim: IVec2 = wall_dim
        self.__cell_dim: IVec2 = cell_dim
        self.__tiles: list[Tile] = []

    def add_tile(self, tile: Tile) -> int:
        res = len(self.__tiles)
        self.__tiles.append(tile)
        return res

    def dst_coord(self, pos: IVec2) -> IVec2:
        return (n := pos // 2) * self.__cell_dim + (pos - n) * self.__wall_dim

    def src_coord(self, pos: IVec2) -> IVec2:
        return pos % 2 * self.__wall_dim

    def tile_size(self, pos: IVec2) -> IVec2:
        return (pos + 1) % 2 * self.__wall_dim + pos % 2 * self.__cell_dim

    def draw_at(self, at: IVec2, idx: int, window: curses.window) -> None:
        self.__tiles[idx].blit(
            self.src_coord(at),
            self.dst_coord(at),
            self.tile_size(at),
            window,
        )

    def draw_at_wrapping(
        self,
        start: IVec2,
        at: IVec2,
        into: IVec2,
        idx: int,
        window: curses.window,
    ) -> None:
        self.__tiles[idx].blit_wrapping(start, at, into, window)


class ScrollablePad:
    def __init__(
        self,
        dims: IVec2,
        constrained: bool = True,
        init_pos: IVec2 = IVec2.splat(0),
    ) -> None:
        self.__pos = init_pos
        self.pad: curses.window = curses.newpad(*dims.yx())
        self.constrained = constrained

    def dims(self) -> IVec2:
        y, x = self.pad.getmaxyx()
        return IVec2(x, y)

    def clamp(self, dims: IVec2) -> None:
        self.__pos = IVec2.with_op(min)(
            IVec2.with_op(max)(self.__pos, dims - self.dims()), IVec2.splat(0)
        )

    def present(self, at: IVec2, into: IVec2, window: curses.window) -> None:
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
        self.pad.overwrite(
            window,
            *pad_start.yx(),
            *draw_start.yx(),
            *draw_end.yx(),
        )

    def move(self, by: IVec2) -> None:
        self.__pos = self.__pos + by

    def scroll(self, by: IVec2) -> None:
        self.move(by * IVec2.splat(-1))


def extract_pairs(
    config: Config, extra_colors: Iterable[ColorPair] = []
) -> dict[ColorPair, int]:
    all_tilemaps = [
        e
        for tilemaps in (
            config.tilemap_empty,
            config.tilemap_full,
            config.tilemap_path,
            config.tilemap_background,
        )
        for e in tilemaps
    ]
    pairs = {
        pair
        for tilemap in all_tilemaps
        for line in tilemap
        for pair, _ in line
    } | set(extra_colors)
    colors = {color for pair in pairs for color in pair}
    var_colors = {color for color in colors if isinstance(color, str)}
    value_colors = {color for color in colors if not isinstance(color, str)}
    color_lookup = {
        "BLACK": curses.COLOR_BLACK,
        "BLUE": curses.COLOR_BLUE,
        "CYAN": curses.COLOR_CYAN,
        "GREEN": curses.COLOR_GREEN,
        "MAGENTA": curses.COLOR_MAGENTA,
        "RED": curses.COLOR_RED,
        "WHITE": curses.COLOR_WHITE,
        "YELLOW": curses.COLOR_YELLOW,
    }
    available_colors = {i for i in range(0, curses.COLORS)}
    res_colors: dict[Color, int] = {}
    for var_color in var_colors:
        if var_color not in color_lookup:
            raise BackendException("Unknown color " + var_color + " in config")
        res_colors[var_color] = color_lookup[var_color]
        available_colors -= {color_lookup[var_color]}
    if len(available_colors) < len(value_colors):
        raise BackendException(
            "Too many value color values in config: "
            + f"maximum: {len(available_colors)}, "
            + f"got: {len(value_colors)}"
        )
    for color, color_number in zip(value_colors, available_colors):
        curses.init_color(
            color_number, *(max(0, min(1000, channel)) for channel in color)
        )
        res_colors[color] = color_number
    available_pairs = {i for i in range(1, curses.COLOR_PAIRS)}
    if len(available_pairs) < len(pairs):
        raise BackendException(
            "Too many color pairs in config: "
            + f"maximum: {len(available_pairs)}, "
            + f"got: {len(pairs)}"
        )
    res_pairs = {}
    for pair, pair_number in zip(pairs, available_pairs):
        fg, bg = pair
        curses.init_pair(pair_number, res_colors[fg], res_colors[bg])
        res_pairs[pair] = curses.color_pair(pair_number)

    return res_pairs


class TileMaps:
    def __init__(
        self,
        config: Config,
        pair_map: dict[ColorPair, int],
        backend: "TTYBackend",
    ) -> None:
        mazetile_dims = config.tilemap_wall_size + config.tilemap_cell_size

        def new_tilemap(lines: list[ColoredLine], dim: IVec2) -> Tile:
            return Tile(
                [
                    [(s, pair_map[color_pair]) for color_pair, s in line]
                    for line in lines
                ],
                dim,
            )

        def add_style(
            tilemap: list[ColoredLine], size: IVec2 = mazetile_dims
        ) -> int:
            return backend.add_style(new_tilemap(tilemap, size))

        self.empty: list[int] = list(map(add_style, config.tilemap_empty))
        self.full: list[int] = list(map(add_style, config.tilemap_full))
        self.path: list[int] = list(map(add_style, config.tilemap_path))
        self.filler: list[int] = list(
            map(
                lambda e: add_style(e, config.tilemap_background_size),
                config.tilemap_background,
            )
        )


class TileCycle[T]:
    def __init__(
        self, styles: list[T], cb: Callable[[T], None], i: int = 0
    ) -> None:
        if len(styles) == 0:
            raise BackendException("No styles provided in tilecycle")
        self.__styles = styles
        self.__cb = cb
        self.__i = i
        cb(styles[i])

    def cycle(self, by: int = 1) -> None:
        new = (self.__i + by) % len(self.__styles)
        if new != self.__i:
            self.__cb(self.__styles[new])
        self.__i = new

    def curr_style(self) -> T:
        return self.__styles[self.__i]


class TTYBackend:
    def __init__(
        self, maze_dims: IVec2, wall_dim: IVec2, cell_dim: IVec2
    ) -> None:
        super().__init__()
        self.__tilemap: MazeTileMap = MazeTileMap(wall_dim, cell_dim)
        self.__style = 0

        dims = self.__tilemap.dst_coord(maze_dims * 2 + 1)

        self.__screen: curses.window = curses.initscr()
        curses.start_color()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)
        self.__screen.keypad(True)

        self.__scratch: curses.window = curses.newpad(1, 1)
        self.__pad: ScrollablePad = ScrollablePad(dims)
        self.__dims = maze_dims

        maze_box = FBox(
            IVec2(BInt(dims.x), BInt(dims.y)),
            lambda at, into: self.__pad.present(at, into, self.__scratch),
        )

        self.__filler_boxes: list[DBox] = []

        def filler_box() -> Box:
            self.__filler_boxes.append(
                res := DBox(
                    FBox(
                        IVec2(BInt(0, True), BInt(0, True)),
                        lambda at, into: (
                            None
                            if self.__filler is None
                            else self.__tilemap.draw_at_wrapping(
                                at, at, into, self.__filler, self.__scratch
                            )
                        ),
                    )
                )
            )
            return res

        f: Callable[[int], int] = lambda e: e
        layout = layout_split(
            layout_fair, layout_sort_chunked(layout_fair, layout_priority, f)
        )
        self.__layout: Box = VBox(
            layout,
            [
                (filler_box(), 0),
                (
                    HBox(
                        layout,
                        [(filler_box(), 0), (maze_box, 1), (filler_box(), 0)],
                    ),
                    1,
                ),
                (filler_box(), 0),
            ],
        )

        self.__resize: bool = False

        self.__filler: None | int = None

        self.__style_bimap: BiMap[int, IVec2] = BiMap()

    def __del__(self) -> None:
        curses.curs_set(1)
        curses.nocbreak()
        self.__screen.keypad(False)
        curses.echo()
        curses.endwin()

    def set_filler(self, style: int) -> None:
        if self.__filler == style:
            return
        self.__filler = style
        for box in self.__filler_boxes:
            box.mark_dirty()

    def get_styled(self, style: int) -> Iterable[IVec2]:
        return self.__style_bimap.get(style)

    def map_style_cb(self) -> Callable[[int], None]:
        curr: int | None = None

        def inner(new: int) -> None:
            nonlocal curr
            if curr is None:
                curr = new
            if curr == new:
                return
            self.set_style(new)
            for tile in self.get_styled(curr):
                self.draw_tile(tile)
            curr = new

        return inner

    def add_style(self, style: Tile) -> int:
        return self.__tilemap.add_tile(style)

    def dims(self) -> IVec2:
        return self.__dims

    def draw_tile(self, pos: IVec2) -> None:
        style = self.__style
        self.__style_bimap.add(style, pos)
        self.__tilemap.draw_at(pos, style, self.__pad.pad)

    def set_style(self, style: int) -> None:
        self.__style = style

    def present(self) -> None:
        if self.__resize:
            self.__resize = False
            self.__screen.erase()
            for box in self.__filler_boxes:
                box.mark_dirty()
        self.__screen.refresh()
        y, x = self.__screen.getmaxyx()
        self.__scratch.resize(y, x)
        self.__layout.laid_out(IVec2(0, 0), IVec2(x, y))
        self.__scratch.overwrite(self.__screen)

    def event(self, timeout_ms: int = -1) -> BackendEvent | bool:
        self.__screen.timeout(timeout_ms)
        try:
            key = self.__screen.getkey()
        except curses.error:
            return False
        match key:
            case "KEY_RESIZE":
                self.__resize = True
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
        return True
