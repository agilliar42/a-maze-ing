from abc import ABC, abstractmethod
from collections.abc import Callable, Generator, Iterable
from dataclasses import dataclass
from mazegen.utils import BiMap
from mazegen.config.config_parser import Color, Config, ColoredLine, ColorPair
from mazegen.display.layout import (
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
from mazegen.utils import Rect, QuadTree, IVec2
import curses

from mazegen.utils.coords import Orientation


class BackendException(Exception):
    pass


@dataclass
class KeyboardInput:
    sym: str


class ITile(ABC):
    """
    The ABC for a tile, for use with screens
    """

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
        """
        Copies data from self into the window
        """
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
        """
        Generator of the coords that would be drawn through a blit, as well
        as subpixels for said blit
        """
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
        """
        Iterates over the subtiles that a wrapping blit would go through,
        as well as where they would be blitted to
        """

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
        """
        Blits self to the window, wrapping the tile
        """
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
        """
        An iterator over the subpixels a wrapping blit would write
        """
        for pos, subtile in self.blit_wrapping_subtiles(
            src, dst, size, justify
        ):
            for e in subtile.blit_iter(IVec2.splat(0), pos, subtile.size()):
                yield e


class Tile(ITile):
    """
    A simple tile that is its entire pad, initliazed from pixel values
    """

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

        pixels = [
            [pixel for pixel in line[: dims.y]] for line in pixels[: dims.y]
        ]

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
    """
    A tile that is just one pixel of its pad
    """

    def __init__(self, tile: ITile, pos: IVec2) -> None:
        super().__init__(tile.pad)
        self.__pos: IVec2 = tile.pos() + pos

    def size(self) -> IVec2:
        return IVec2.splat(1)

    def pos(self) -> IVec2:
        return self.__pos


class SubTile(ITile):
    """
    A tile that is a sub-section of its pad
    """

    def __init__(self, tile: ITile, pos: IVec2, size: IVec2) -> None:
        super().__init__(tile.pad)
        self.__pos: IVec2 = tile.pos() + pos
        self.__size: IVec2 = size

    def size(self) -> IVec2:
        return self.__size

    def pos(self) -> IVec2:
        return self.__pos


class MazeTileMap:
    """
    A tilemap of tiles, for use in displaying
    """

    def __init__(self, wall_dim: IVec2, cell_dim: IVec2) -> None:
        self.__wall_dim: IVec2 = wall_dim
        self.__cell_dim: IVec2 = cell_dim
        self.tiles: list[ITile] = []

    def add_tile(self, tile: ITile) -> int:
        """
        Adds a tile to the tilemap and returns its index
        """
        res = len(self.tiles)
        self.tiles.append(tile)
        return res

    def dst_coord(self, pos: IVec2) -> IVec2:
        """
        Returns the coordinate in the output window from a tile coordinate
        """
        return (n := pos // IVec2.splat(2)) * self.__cell_dim + (
            pos - n
        ) * self.__wall_dim

    def src_coord(self, pos: IVec2) -> IVec2:
        """
        Returns the coordinate in a tile in the tilemap from a tile coordinate
        """
        return pos % IVec2.splat(2) * self.__wall_dim

    def dst_coord_rev(self, pixel: IVec2) -> IVec2:
        """
        Returns the coordinate of a tile from the coordinate in the
        destination window
        """
        mod = self.__wall_dim + self.__cell_dim
        return (pixel // mod) * IVec2.splat(2) + (pixel % mod).with_op(
            lambda a, b: 0 if a < b else 1, self.__wall_dim
        )

    def tile_size(self, pos: IVec2) -> IVec2:
        """
        Returns the size of the destination tile for a given tile coord
        """
        return (pos + IVec2.splat(1)) % IVec2.splat(
            2
        ) * self.__wall_dim + pos % IVec2.splat(2) * self.__cell_dim

    def draw_at(self, at: IVec2, idx: int, window: curses.window) -> None:
        """
        Draws the given tile at tile position into the window
        """
        self.tiles[idx].blit(
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
        """
        Draws the given tile to an area in the window specified in pixel
        coord, wrapping
        """
        self.tiles[idx].blit_wrapping(start, at, into, window)


class ScrollablePad:
    """
    A pad that may be used for display objects too large to fit, which may be
    scrolled
    """

    def __init__(
        self,
        dims: IVec2,
        cb: Callable[[Rect], None],
        constrained: bool = True,
        init_pos: IVec2 = IVec2.splat(0),
    ) -> None:
        self.__pos = init_pos
        self.pad: curses.window = curses.newpad(*dims.yx())
        self.constrained = constrained
        self.cb = cb

    def dims(self) -> IVec2:
        y, x = self.pad.getmaxyx()
        return IVec2(x, y)

    def clamp(self, dims: IVec2) -> None:
        """
        Clamps this tile's coordinates to fit within dims, not scrolling past
        """
        self.__pos = self.__pos.lane_max(dims - self.dims()).lane_min(
            IVec2.splat(0)
        )

    def present(self, at: IVec2, into: IVec2, window: curses.window) -> None:
        """
        Draws this pad at the location on the window
        """
        if self.constrained:
            self.clamp(into)

        pad_start = (IVec2.splat(0) - self.__pos).lane_max(IVec2.splat(0))
        win_start = self.__pos.lane_max(IVec2.splat(0))
        draw_dim = (self.dims() - pad_start).lane_min(into - win_start)
        if draw_dim.x <= 0 or draw_dim.y <= 0:
            return
        draw_start = at + win_start
        draw_end = draw_start + draw_dim - IVec2.splat(1)
        self.cb((pad_start, pad_start + draw_dim))
        self.pad.overwrite(
            window,
            *pad_start.yx(),
            *draw_start.yx(),
            *draw_end.yx(),
        )

    def move(self, by: IVec2) -> None:
        """
        Moves the tile itself, opposite of scroll
        """
        self.__pos = self.__pos + by

    def scroll(self, by: IVec2) -> None:
        """
        Scrolls through the tile, opposite of move
        """
        self.move(by * IVec2.splat(-1))


def extract_pairs(
    config: Config, extra_colors: Iterable[ColorPair] = []
) -> dict[ColorPair, int]:
    """
    Extracts the color pairs from the config, and maps them to text
    attributes
    May raise a backend exception if too many colors are used or an invalid
    variable color is used
    """
    all_tilemaps = [
        e
        for tilemaps in (
            config.tilemap_empty,
            config.tilemap_full,
            config.tilemap_path,
            config.tilemap_background,
        )
        for e in tilemaps
    ] + [config.tilemap_box, config.prompt]
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
    """
    A class to store all the tilemaps once extracted from the config
    """

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

        box = new_tilemap(
            config.tilemap_box,
            config.tilemap_box_size * IVec2.splat(3)
            + config.tilemap_box_bridge_size,
        )

        self.box: list[list[int]] = []
        corner = config.tilemap_box_size
        bridge = config.tilemap_box_bridge_size
        y = 0
        for height in (corner.y, bridge.y, corner.y, corner.y):
            x = 0
            line: list[int] = []
            for width in (corner.x, bridge.x, corner.x, corner.x):
                tile = SubTile(box, IVec2(x, y), IVec2(width, height))
                line.append(backend.add_style(tile))
                x += width
            self.box.append(line)
            y += height
        self.prompt: int = add_style(config.prompt, config.prompt_size)


class TileCycle[T]:
    """
    A store of tile styles, used to cycle through them
    """

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
        """
        Cycles the current style by a given amount
        """
        new = abs((self.__i + by) % len(self.__styles))
        if new != self.__i:
            self.__cb(self.__styles[new])
        self.__i = new

    def curr_style(self) -> T:
        """
        Returns the current style
        """
        return self.__styles[self.__i]


class TTYBackend:
    """
    This class stores a lot of things, which may be better split but that's
    a lot of work
    This initializes everything required for the display, that is, the
    tilemaps, the curses api, the color pairs, and the entire window
    layout
    May raise a BackendException if it fails to excract colors
    """

    def __init__(
        self,
        config: Config,
    ) -> None:
        super().__init__()
        self.__tilemap: MazeTileMap = MazeTileMap(
            config.tilemap_wall_size, config.tilemap_cell_size
        )
        self.__style = 0
        self.__dims = IVec2(config.width, config.height)

        dims = self.__tilemap.dst_coord(
            self.__dims * IVec2.splat(2) + IVec2.splat(1)
        )

        self.__uninit: bool = False
        self.__screen: curses.window = curses.initscr()
        self.__screen.timeout(0)
        curses.start_color()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)
        self.__screen.keypad(True)

        pair_map = extract_pairs(config)
        self.tilemaps = TileMaps(config, pair_map, self)

        self.__scratch: curses.window = curses.newpad(1, 1)
        self.__drawn: QuadTree = QuadTree()
        self.__pad: ScrollablePad = ScrollablePad(dims, self.pad_callback)

        self.__filler_boxes: list[DBox] = []

        def filler_box(
            dims: IVec2[BInt] = IVec2(BInt(0, True), BInt(0, True))
        ) -> Box:
            self.__filler_boxes.append(
                res := DBox(
                    FBox(
                        dims,
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

        def border_box(x: int, y: int, orient: Orientation | None) -> Box:
            tile = self.tilemaps.box[y][x]
            dims = self.__tilemap.tiles[tile].size()
            box_dims = IVec2(BInt(0, True), BInt(0, True))
            match orient:
                case Orientation.HORIZONTAL:
                    box_dims.y = BInt(dims.y)
                case Orientation.VERTICAL:
                    box_dims.x = BInt(dims.x)
                case None:
                    box_dims.x = BInt(dims.x)
                    box_dims.y = BInt(dims.y)

            return FBox(
                box_dims,
                lambda at, into: self.__tilemap.draw_at_wrapping(
                    IVec2(0, 0), at, into, tile, self.__scratch
                ),
            )

        f: Callable[[int], int] = lambda e: e
        layout = layout_split(
            layout_fair, layout_sort_chunked(layout_fair, layout_priority, f)
        )

        def fullpadded(box: Box) -> Box:
            return VBox(
                layout,
                [
                    (filler_box(), 0),
                    (
                        HBox(
                            layout,
                            [
                                (filler_box(), 0),
                                (box, 1),
                                (filler_box(), 0),
                            ],
                        ),
                        1,
                    ),
                    (filler_box(), 0),
                ],
            )

        maze_box: Box = FBox(
            IVec2(BInt(dims.x), BInt(dims.y)),
            lambda at, into: self.__pad.present(at, into, self.__scratch),
        )
        maze_box = fullpadded(maze_box)
        prompt_box: Box = FBox(
            IVec2(BInt(config.prompt_size.x), BInt(config.prompt_size.y)),
            lambda at, into: self.__tilemap.draw_at_wrapping(
                IVec2.splat(0), at, into, self.tilemaps.prompt, self.__scratch
            ),
        )
        prompt_box = fullpadded(prompt_box)

        def border_line_box(y: int) -> Box:
            return HBox.noassoc(
                layout_fair,
                [
                    border_box(0, y, None),
                    border_box(1, y, Orientation.HORIZONTAL),
                    border_box(3, y, None),
                ],
            )

        def border_column_sides(box: Box) -> Box:
            return HBox.noassoc(
                layout_fair,
                [
                    border_box(0, 1, Orientation.VERTICAL),
                    box,
                    border_box(3, 1, Orientation.VERTICAL),
                ],
            )

        self.__layout: Box = VBox.noassoc(
            layout_fair,
            [
                border_line_box(0),
                border_column_sides(maze_box),
                border_line_box(2),
                border_column_sides(prompt_box),
                border_line_box(3),
            ],
        )

        self.__redraw: bool = True

        self.__filler: None | int = None

        self.__style_bimap: BiMap[int, IVec2] = BiMap()
        self.__bg_init: Callable[[IVec2], int] | None = None

    def __del__(self) -> None:
        self.uninit()

    def uninit(self) -> None:
        """
        Uninitializes self, such resetting the terminal to its previous state
        """
        if self.__uninit:
            return
        self.__uninit = True
        curses.curs_set(1)
        curses.nocbreak()
        self.__screen.keypad(False)
        curses.echo()
        curses.endwin()

    def pad_callback(self, rect: Rect) -> None:
        """
        The function to be called with the window area where the maze pad
        should be drawn
        """
        start, end_excl = rect
        drawn_rect = (
            self.__tilemap.dst_coord_rev(start),
            self.__tilemap.dst_coord_rev(end_excl - IVec2.splat(1))
            + IVec2.splat(1),
        )
        drawn_tree = QuadTree.rectangle(drawn_rect)
        redrawn = drawn_tree - self.__drawn
        for tile in redrawn.tiles():
            if self.__style_bimap.revcontains(tile):
                style = self.__style_bimap.revget(tile)
                self.set_style(style)
                self.draw_tile(tile)
            elif self.__bg_init is not None:
                self.set_style(self.__bg_init(tile))
                self.draw_tile(tile)
        self.__drawn += drawn_tree

    def set_filler(self, style: int) -> None:
        """
        Changes the filler style used for the window layout
        """
        if self.__filler == style:
            return
        self.__redraw = True
        self.__filler = style
        for box in self.__filler_boxes:
            box.mark_dirty()

    def set_bg_init(self, bg_init: Callable[[IVec2], int]) -> None:
        """
        Sets the function for use to initialize the background of the maze
        """
        self.__bg_init = bg_init

    def get_style_height(self, style: int) -> int:
        """
        Returns the tree height of the given style, if zero it means
        no tile uses this style
        """
        return self.__style_bimap.get(style).height()

    def map_style(self, src: int, dst: int) -> None:
        """
        Maps the src style to dst, such that any tile with src style currently
        will be redrawn with dst from now on
        """
        if src == dst:
            return
        if self.get_style_height(src) != 0:
            self.__redraw = True
            self.__drawn = QuadTree()
            self.__style_bimap.key_map(src, dst)

    def map_style_cb(self) -> Callable[[int], None]:
        """
        The callback to use when one wants to initliaze then map consecutive
        styles, for use with tile cycles
        """
        curr: int | None = None

        def inner(new: int) -> None:
            nonlocal curr
            if curr is None:
                curr = new
            self.map_style(curr, new)
            curr = new

        return inner

    def add_style(self, style: ITile) -> int:
        """
        Adds the given style to the tilemap, and returns its index
        """
        return self.__tilemap.add_tile(style)

    def dims(self) -> IVec2:
        """
        Returns the dimensions of the maze
        """
        return self.__dims

    def draw_tile(self, pos: IVec2) -> None:
        """
        Draws a tile at the pos with the current style
        """
        style = self.__style
        self.__style_bimap.add(style, pos)
        self.__tilemap.draw_at(pos, style, self.__pad.pad)
        self.__redraw = True

    def set_style(self, style: int) -> None:
        """
        Sets the current style
        """
        self.__style = style

    def present(self) -> None:
        """
        Redraw and layout the screen
        """
        if not self.__redraw:
            return
        self.__redraw = False
        self.__screen.refresh()
        y, x = self.__screen.getmaxyx()
        self.__scratch.resize(y, x)
        self.__layout.laid_out(IVec2(0, 0), IVec2(x, y))
        self.__scratch.overwrite(self.__screen)

    def event(self) -> KeyboardInput | bool:
        """
        Poll for a keyboard input, some of which may already get handled
        for scrolling
        """
        try:
            key = self.__screen.getkey()
        except curses.error:
            return False

        match key:
            case "KEY_RESIZE":
                self.__screen.erase()
                for box in self.__filler_boxes:
                    box.mark_dirty()
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
        self.__redraw = True
        return True
