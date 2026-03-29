from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, Type, cast

from mazegen.utils import IVec2
from .parser_combinator import (
    ParseError,
    ParseResult,
    Parser,
    alt,
    ascii_digit,
    cut,
    delimited,
    eof_parser,
    fold,
    lookahead_parser,
    many,
    many_count,
    none_of,
    nonempty_parser,
    null_parser,
    one_of,
    pair,
    parser_complete,
    parser_map,
    parser_map_err,
    preceeded,
    recognize,
    seq,
    tag,
    terminated,
    value,
)


def parse_bool(s: str) -> ParseResult[bool]:
    """
    Parses a boolean, with its first letter a capital
    """
    return parser_map_err(
        lambda e: ParseError("Expected boolean 'True' or 'False'", e.at),
        alt(
            value(True, tag("True")),
            value(False, tag("False")),
        ),
    )(s)


def parse_int(s: str) -> ParseResult[int]:
    """
    Parses an unsigned integer
    """
    return parser_map_err(
        lambda e: ParseError("Expected integer literal", e.at),
        parser_map(int, recognize(many_count(ascii_digit, min_n=1))),
    )(s)


def multispace0(s: str) -> ParseResult[str]:
    """
    Parses zero or more spaces or tabs
    """
    return recognize(many_count(one_of(" \t")))(s)


def parse_comment(s: str) -> ParseResult[str]:
    """
    Parses a python-style comment, that is a `#`, and all following characters
    up to a newline
    """
    return recognize(seq(tag("#"), many_count(none_of("\n"))))(s)


def spaced[T](parser: Parser[T]) -> Parser[T]:
    """
    Makes the given parser be surrounded by multispace0, allowing for spaces
    before and after
    """
    return delimited(multispace0, parser, multispace0)


def parse_coord(s: str) -> ParseResult[IVec2]:
    """
    Parses coordinates, that is two int separated by a spaced comma
    """
    return parser_map(
        lambda e: IVec2(*e),
        pair(
            terminated(
                parse_int,
                spaced(tag(",")),
            ),
            parse_int,
        ),
    )(s)


def parse_path(s: str) -> ParseResult[str]:
    """
    Parses a file path, which simply recognizes any character except a newline
    Requires at least one character
    """
    return recognize(many_count(none_of("\n"), min_n=1))(s)


def char_range(a: str, b: str) -> str:
    """
    A simple function to create a string from a range of characters
    """
    res = ""
    for c in range(ord(a), ord(b) + 1):
        res = res + chr(c)
    return res


def parse_varname(s: str) -> ParseResult[str]:
    """
    Parses a variable name, that is one alphabetic or underscore character,
    followed by zero or more alphanumeric or unerscore characters
    """
    varstart = "_" + char_range("a", "z") + char_range("A", "Z")
    vartail = varstart + char_range("0", "9")
    return parser_map_err(
        lambda e: ParseError("Expected color identifier", e.at),
        recognize(seq(one_of(varstart), many_count(one_of(vartail)))),
    )(s)


type Color = tuple[int, int, int] | str
type ColorPair = tuple[Color, Color]

type ColoredLine = list[tuple[ColorPair, str]]
type Grouped[T] = tuple[int, T]


def parse_color(s: str) -> ParseResult[Color]:
    """
    Parses a color, which is either a variable name, or three integers
    separated by spaced comma
    """
    cut_comma = spaced(
        cut(lookahead_parser(tag(","), seq(multispace0, parse_int)))
    )
    try:
        return cast(
            ParseResult[Color],
            alt(
                parser_map(
                    tuple,
                    many(parse_int, 3, 3, cut_comma),
                ),
                parse_varname,
            )(s),
        )
    except ParseError as e:
        return e


def parse_color_pair(s: str) -> ParseResult[ColorPair]:
    """
    Parses a color pair, that is two colors separated by a spaced colon
    """
    return cast(
        ParseResult[ColorPair],
        parser_map(
            tuple,
            many(parse_color, 2, 2, spaced(tag(":"))),
        )(s),
    )


def parse_colored_line(
    s: str,
) -> ParseResult[ColoredLine]:
    """
    Parses a colored line, that is a sequence of possibly escaped strings
    of characters, each preceeded by a color pair surrounded by braces,
    all of which is surrounded by double quotes
    """

    color_prefix = delimited(
        tag("{"), cut(spaced(parse_color_pair)), cut(tag("}"))
    )
    noncolor_str = fold(
        alt(
            none_of('\n{}\\"'),
            preceeded(
                tag("\\"),
                cut(
                    alt(
                        value("{", tag("{")),
                        value("}", tag("}")),
                        value("\\", tag("\\")),
                        value('"', tag('"')),
                    )
                ),
            ),
        ),
        lambda a, b: a + b,
        lambda: "",
    )

    return spaced(
        delimited(
            tag('"'),
            many(pair(color_prefix, cut(noncolor_str))),
            parser_map_err(
                lambda e: ParseError("Expected color prefix or '\"'", e.at),
                tag('"'),
            ),
        )
    )(s)


def parse_str_line(s: str) -> ParseResult[str]:
    """
    Parses a single line string with no escapes
    """
    return spaced(
        delimited(
            tag('"'),
            recognize(
                many_count(
                    none_of('"\n'),
                )
            ),
            tag('"'),
        )
    )(s)


def grouped_parser[T](parser: Parser[T]) -> Parser[Grouped[T]]:
    """
    Returns a parser that first parses a spaced int, or assumes zero, followed
    by the given parser, giving a tuple of the two
    """
    return pair(alt(spaced(parse_int), value(0, null_parser)), parser)


class ConfigError(Exception):
    """
    A simple exception for filtering, raised when a field is set an invalid
    amount of times, or when certain config invariants are not held up
    """


class ConfigField[T, U = T](ABC):
    """
    A field in the config, defining methods to parse it, and how to resolve
    multiple definitions
    """

    def __init__(
        self,
        name: str,
    ) -> None:
        self.__name = name

    @abstractmethod
    def parse(self, s: str) -> ParseResult[T]: ...

    def default(self) -> U:
        raise ConfigError(f"Value {self.__name} not provided")

    @abstractmethod
    def merge(self, vals: list[T]) -> U: ...

    def name(self) -> str:
        return self.__name


class SimpleField[T](ConfigField[T, T]):
    """
    A simlpe imlpementation of ConfigField, simply using the default if no
    value was provided, giving the value if only one was specified, raising
    an error otherwise
    """

    def merge(self, vals: list[T]) -> T:
        if len(vals) == 0:
            return self.default()
        if len(vals) == 1:
            return vals[0]
        raise ConfigError(
            f"More than one definition of config field {self.__name}"
        )


class IntField(SimpleField[int]):
    """
    A config field that parses an integer
    """

    def parse(self, s: str) -> ParseResult[int]:
        return parse_int(s)


class BoolField(SimpleField[bool]):
    """
    A config field that parses a boolean
    """

    def parse(self, s: str) -> ParseResult[bool]:
        return parse_bool(s)


class CoordField(SimpleField[IVec2]):
    """
    A config field that parses a coordinate
    """

    def parse(self, s: str) -> ParseResult[IVec2]:
        return parse_coord(s)


class PathField(SimpleField[str]):
    """
    A config field that parses a file path
    """

    def parse(self, s: str) -> ParseResult[str]:
        return parse_path(s)


def OptionalField[T, U](
    cls: Type[ConfigField[T, U]],
) -> Type[ConfigField[T, U | None]]:
    """
    Maps the config field to be None, resovling to it if no value was given
    """
    return DefaultedField(cls, None)


def DefaultedField[T, U](
    cls: Type[ConfigField[T, U]], default: U
) -> Type[ConfigField[T, U]]:
    """
    Maps the config field to resovle to a default if no value was given
    """

    class Inner(cls):  # type: ignore
        def default(self) -> U:
            return default

        def merge(self, vals: list[T]) -> U:
            return cls.merge(self, vals) if len(vals) > 0 else self.default()

    return Inner


def DefaultedStrField[T, U](
    cls: Type[ConfigField[T, U]], default_strs: list[str]
) -> Type[ConfigField[T, U]]:
    """
    Same as DefaultedField except the default value is parsed from the list
    of strings
    """

    class Inner(cls):  # type: ignore
        def default(self) -> U:
            acc = []
            for s in default_strs:
                res = parser_complete(self.parse)(s)
                if isinstance(res, ParseError):
                    raise Exception(
                        "Failed to construct defaulted field " + self.name()
                    )
                acc.append(res[0])
            return self.merge(acc)

        def merge(self, vals: list[T]) -> U:
            return cls.merge(self, vals) if len(vals) > 0 else self.default()

    return Inner


def MappedField[T, U, V](
    cls: Type[ConfigField[T, U]], mapping: Callable[[U], V]
) -> Type[ConfigField[T, V]]:
    """
    Maps a field to apply the given function to its output
    """

    class Inner(ConfigField[T, V]):
        def __init__(self, name: str) -> None:
            self.__inner = cls(name)
            super().__init__(name)

        def parse(self, s: str) -> ParseResult[T]:
            return self.__inner.parse(s)

        def default(self) -> V:
            return mapping(self.__inner.default())

        def merge(self, vals: list[T]) -> V:
            res = mapping(self.__inner.merge(vals))
            return res

    return Inner


def ListField[T](parser: Parser[T]) -> Type[ConfigField[list[T]]]:
    """
    A field that resolves multiple instances of a field by putting them in
    a list.
    Defaults to an empty list
    """

    class Inner(ConfigField[list[T]]):
        def parse(self, s: str) -> ParseResult[list[T]]:
            return parser_map(lambda e: [e], parser)(s)

        def default(self) -> list[T]:
            return []

        def merge(self, vals: list[list[T]]) -> list[T]:
            return (
                [e for val in vals for e in val]
                if len(vals) > 0
                else self.default()
            )

    return Inner


def map_grouped[T](vals: list[Grouped[T]]) -> list[list[T]]:
    """
    Takse a list of grouped-by-integer elements, and separates them into
    multiple lists, one per distinct integer
    """
    res: dict[int, list[T]] = {}
    for group, elem in vals:
        if group not in res:
            res[group] = []
        res[group].append(elem)
    return list(res.values())


ColoredLineField = MappedField(
    ListField(grouped_parser(parse_colored_line)), map_grouped
)

PatternField = ListField(parse_str_line)


def line_parser[T](
    fields: dict[str, ConfigField[T]],
) -> Parser[tuple[str, T] | None]:
    """
    Parses a line from any of the given fields, or an empty/comment line
    Expects the name of the parser, followed by an equal sign, and then
    the field itself, each of which may be spaced
    """
    return parser_map_err(
        lambda e: ParseError("Expected valid field name", e.at),
        alt(
            parser_map(lambda _: None, parse_comment),
            *(
                preceeded(
                    seq(spaced(tag(name)), tag("=")),
                    spaced(
                        parser_map(
                            (lambda name: lambda res: (name, res))(name),
                            cut(terminated(field.parse, multispace0)),
                        )
                    ),
                )
                for name, field in fields.items()
            ),
            parser_map(
                lambda _: None, lookahead_parser(multispace0, tag("\n"))
            ),
        ),
    )


def fields_parser(
    fields_raw: dict[str, type[ConfigField[Any]]],
) -> Parser[dict[str, Any]]:
    """
    A general parser for all the given fields
    Initializes the config field classes with their name as argument, then
    applies a line parser created from them repeatedly, then finally resolves
    the multiple definitions with the field's implementation
    Returns a dict of the name of the field to its resolved output
    """
    fields = {key: cls(key) for key, cls in fields_raw.items()}
    parse_line = nonempty_parser(
        cut(
            terminated(
                line_parser(fields),
                parser_map_err(
                    lambda e: ParseError("Expected newline or EOF", e.at),
                    alt(tag("\n"), eof_parser()),
                ),
            )
        )
    )

    def inner(s: str) -> ParseResult[dict[str, Any]]:
        def fold_fn(
            acc: dict[str, list[Any]], elem: tuple[str, Any] | None
        ) -> dict[str, list[Any]]:
            if elem is not None:
                acc[elem[0]].append(elem[1])
            return acc

        fields_map: Callable[[dict[str, list[Any]]], dict[str, Any]] = (
            lambda res: {
                name: fields[name].merge(values)
                for name, values in res.items()
            }
        )

        def default_lists(d: dict[str, list[Any]]) -> dict[str, list[Any]]:
            for field in fields.keys():
                if field not in d:
                    d[field] = []
            return d

        return parser_map(
            fields_map,
            parser_map(
                default_lists,
                parser_complete(
                    fold(
                        parse_line,
                        fold_fn,
                        lambda: {name: [] for name in fields.keys()},
                    )
                ),
            ),
        )(s)

    return inner


class Config:
    """
    The config as parsed from a file
    """

    width: int
    height: int
    entry: IVec2 | None
    exit: IVec2 | None
    output_file: str
    perfect: bool
    seed: int | None
    screensaver: bool
    visual: bool
    tilemap_wall_size: IVec2
    tilemap_cell_size: IVec2
    tilemap_full: list[list[ColoredLine]]
    tilemap_empty: list[list[ColoredLine]]
    tilemap_path: list[list[ColoredLine]]
    tilemap_entry: list[list[ColoredLine]]
    tilemap_exit: list[list[ColoredLine]]
    tilemap_background_size: IVec2
    tilemap_background: list[list[ColoredLine]]
    tilemap_box_size: IVec2
    tilemap_box_bridge_size: IVec2
    tilemap_box: list[ColoredLine]
    prompt_size: IVec2
    prompt: list[ColoredLine]
    maze_pattern: list[str]

    @staticmethod
    def parse(s: str) -> "Config":
        """
        Parses the config from a string, defaulting values as needed
        May raise a ParserError or ConfigError
        """
        from mazegen.maze import Pattern

        fields = parser_complete(
            fields_parser(
                {
                    "WIDTH": IntField,
                    "HEIGHT": IntField,
                    "ENTRY": OptionalField(CoordField),
                    "EXIT": OptionalField(CoordField),
                    "OUTPUT_FILE": PathField,
                    "PERFECT": DefaultedField(BoolField, True),
                    "SEED": OptionalField(IntField),
                    "SCREENSAVER": DefaultedField(BoolField, False),
                    "VISUAL": DefaultedField(BoolField, False),
                    "TILEMAP_WALL_SIZE": DefaultedField(
                        CoordField, IVec2(2, 1)
                    ),
                    "TILEMAP_CELL_SIZE": DefaultedField(
                        CoordField, IVec2(2, 1)
                    ),
                    "TILEMAP_FULL": DefaultedStrField(
                        ColoredLineField,
                        [
                            '1"{WHITE:WHITE}    "',
                            '1"{WHITE:WHITE}    "',
                            '2"{MAGENTA:MAGENTA}    "',
                            '2"{MAGENTA:MAGENTA}    "',
                        ],
                    ),
                    "TILEMAP_EMPTY": DefaultedStrField(
                        ColoredLineField,
                        ['"{BLACK:BLACK}    "', '"{BLACK:BLACK}    "'],
                    ),
                    "TILEMAP_PATH": DefaultedStrField(
                        ColoredLineField,
                        [
                            '1"{BLUE:BLUE}    "',
                            '1"{BLUE:BLUE}    "',
                            '2"{RED:RED}    "',
                            '2"{RED:RED}    "',
                        ],
                    ),
                    "TILEMAP_ENTRY": DefaultedStrField(
                        ColoredLineField,
                        [
                            '1"{WHITE:BLUE}####"',
                            '1"{WHITE:BLUE}####"',
                            '2"{WHITE:RED}####"',
                            '2"{WHITE:RED}####"',
                        ],
                    ),
                    "TILEMAP_EXIT": DefaultedStrField(
                        ColoredLineField,
                        [
                            '1"{BLACK:BLUE}####"',
                            '1"{BLACK:BLUE}####"',
                            '2"{BLACK:RED}####"',
                            '2"{BLACK:RED}####"',
                        ],
                    ),
                    "TILEMAP_BACKGROUND_SIZE": DefaultedField(
                        CoordField, IVec2(4, 2)
                    ),
                    "TILEMAP_BACKGROUND": DefaultedStrField(
                        ColoredLineField,
                        ['"{BLACK:BLACK}    "', '"{BLACK:BLACK}    "'],
                    ),
                    "MAZE_PATTERN": DefaultedField(
                        PatternField, Pattern.FT_PATTERN
                    ),
                    "TILEMAP_BOX_SIZE": DefaultedField(
                        CoordField, IVec2(1, 1)
                    ),
                    "TILEMAP_BOX_BRIDGE_SIZE": DefaultedField(
                        CoordField, IVec2(1, 1)
                    ),
                    "TILEMAP_BOX": DefaultedStrField(
                        ListField(parse_colored_line),
                        [
                            '"{RED:BLACK}╔═╦╗"',
                            '"{RED:BLACK}║ ║║"',
                            '"{RED:BLACK}╠═╬╣"',
                            '"{RED:BLACK}╚═╩╝"',
                        ],
                    ),
                    "PROMPT_SIZE": DefaultedField(CoordField, IVec2(32, 5)),
                    "PROMPT": DefaultedStrField(
                        ListField(parse_colored_line),
                        [
                            '"{WHITE:BLACK}                                "',
                            '"{WHITE:BLACK} q: quit         r: regenerate  "',
                            '"{WHITE:BLACK} c: color next   k: play/pause  "',
                            '"{WHITE:BLACK} v: color prev   p: toggle path "',
                            '"{WHITE:BLACK}                                "',
                        ],
                    ),
                }
            )
        )(s)
        if isinstance(fields, ParseError):
            raise fields
        res = Config()
        for key, val in fields[0].items():
            res.__dict__[key.lower()] = val

        if res.screensaver:
            res.visual = True

        if res.entry is not None:
            if res.entry.x >= res.width or res.entry.y >= res.height:
                raise ConfigError(
                    f"The given entry {res.entry} is out of bounds of the maze"
                )
        if res.exit is not None:
            if res.exit.x >= res.width or res.exit.y >= res.height:
                raise ConfigError(
                    f"The given exit {res.exit} is out of bounds of the maze"
                )

        return res
