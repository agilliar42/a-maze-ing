from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, Type, cast

from mazegen.utils import IVec2
from .parser_combinator import (
    ParseResult,
    Parser,
    alt,
    ascii_digit,
    cut,
    delimited,
    fold,
    many,
    many_count,
    none_of,
    null_parser,
    one_of,
    pair,
    parser_complete,
    parser_map,
    preceeded,
    recognize,
    seq,
    tag,
    terminated,
    value,
)


def parse_bool(s: str) -> ParseResult[bool]:
    return alt(value(True, tag("True")), value(False, tag("False")))(s)


def parse_int(s: str) -> ParseResult[int]:
    return parser_map(int, recognize(many_count(ascii_digit, min_n=1)))(s)


def multispace0(s: str) -> ParseResult[str]:
    return recognize(many_count(one_of(" \t")))(s)


def parse_comment(s: str) -> ParseResult[str]:
    return recognize(seq(tag("#"), many_count(none_of("\n"))))(s)


def parse_empty_line(s: str) -> ParseResult[None]:
    return (None, s) if s.startswith("\n") else None


def spaced[T](parser: Parser[T]) -> Parser[T]:
    return delimited(multispace0, parser, multispace0)


def parse_coord(s: str) -> ParseResult[IVec2]:
    return parser_map(
        lambda e: IVec2(*e),
        pair(
            terminated(
                parse_int,
                delimited(multispace0, tag(","), multispace0),
            ),
            parse_int,
        ),
    )(s)


def parse_path(s: str) -> ParseResult[str]:
    return recognize(many_count(none_of("\n"), min_n=1))(s)


def char_range(a: str, b: str) -> str:
    res = ""
    for c in range(ord(a), ord(b) + 1):
        res = res + chr(c)
    return res


def parse_varname(s: str) -> ParseResult[str]:
    varstart = "_" + char_range("a", "z") + char_range("A", "Z")
    vartail = varstart + char_range("0", "9")
    return recognize(seq(one_of(varstart), many_count(one_of(vartail))))(s)


type Color = tuple[int, int, int] | str
type ColorPair = tuple[Color, Color]

type ColoredLine = list[tuple[ColorPair, str]]
type Grouped[T] = tuple[int, T]


def parse_color(s: str) -> ParseResult[Color]:
    return cast(
        ParseResult[Color],
        alt(
            parser_map(
                tuple,
                many(parse_int, 3, 3, spaced(tag(","))),
            ),
            parse_varname,
        )(s),
    )


def parse_color_pair(s: str) -> ParseResult[ColorPair]:
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
    returns a list of a color pair variable associated with its string
    """

    color_prefix = delimited(
        tag("{"), cut(spaced(parse_color_pair)), cut(tag("}"))
    )
    noncolor_str = fold(
        alt(
            none_of('\n{\\"'),
            preceeded(
                tag("\\"),
                cut(
                    alt(
                        value("{", tag("{")),
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
            tag('"'), many(pair(color_prefix, cut(noncolor_str))), tag('"')
        )
    )(s)


def parse_str_line(s: str) -> ParseResult[str]:
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
    return pair(alt(spaced(parse_int), value(0, null_parser)), parser)


class ConfigException(Exception):
    pass


class ConfigField[T, U = T](ABC):
    def __init__(
        self,
        name: str,
    ) -> None:
        self.__name = name

    @abstractmethod
    def parse(self, s: str) -> ParseResult[T]: ...

    def default(self) -> U:
        raise ConfigException(
            f"Value {self.__name} not provided, "
            + "and no default value exists"
        )

    @abstractmethod
    def merge(self, vals: list[T]) -> U: ...

    def name(self) -> str:
        return self.__name


class SimpleField[T](ConfigField[T, T]):
    def merge(self, vals: list[T]) -> T:
        if len(vals) == 0:
            return self.default()
        if len(vals) == 1:
            return vals[0]
        raise ConfigException(
            f"More than one definition of config field {self.__name}"
        )


class IntField(SimpleField[int]):
    def parse(self, s: str) -> ParseResult[int]:
        return parse_int(s)


class BoolField(SimpleField[bool]):
    def parse(self, s: str) -> ParseResult[bool]:
        return parse_bool(s)


class CoordField(SimpleField[IVec2]):
    def parse(self, s: str) -> ParseResult[IVec2]:
        return parse_coord(s)


class PathField(SimpleField[str]):
    def parse(self, s: str) -> ParseResult[str]:
        return parse_path(s)


def OptionalField[T, U](
    cls: Type[ConfigField[T, U]],
) -> Type[ConfigField[T, U | None]]:
    return DefaultedField(cls, None)


def DefaultedField[T, U](
    cls: Type[ConfigField[T, U]], default: U
) -> Type[ConfigField[T, U]]:
    class Inner(cls):  # type: ignore
        def default(self) -> U:
            return default

        def merge(self, vals: list[T]) -> U:
            return cls.merge(self, vals) if len(vals) > 0 else self.default()

    return Inner


def DefaultedStrField[T, U](
    cls: Type[ConfigField[T, U]], default_strs: list[str]
) -> Type[ConfigField[T, U]]:
    class Inner(cls):  # type: ignore
        def default(self) -> U:
            acc = []
            for s in default_strs:
                res = self.parse(s)
                if res is None or res[1] != "":
                    raise ConfigException(
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


def ListParser[T](parser: Parser[T]) -> Type[ConfigField[list[T]]]:
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
    res: dict[int, list[T]] = {}
    for group, elem in vals:
        if group not in res:
            res[group] = []
        res[group].append(elem)
    return list(res.values())


ColoredLineField = MappedField(
    ListParser(grouped_parser(parse_colored_line)), map_grouped
)

PatternField = ListParser(parse_str_line)


def line_parser[T](
    fields: dict[str, ConfigField[T]],
) -> Parser[tuple[str, T] | None]:
    return alt(
        parser_map(lambda _: None, parse_comment),
        *(
            preceeded(
                seq(tag(name), multispace0, tag("="), multispace0),
                parser_map(
                    (lambda name: lambda res: (name, res))(name),
                    cut(terminated(field.parse, multispace0)),
                ),
            )
            for name, field in fields.items()
        ),
        parser_map(lambda _: None, parse_empty_line),
    )


def fields_parser(
    fields_raw: dict[str, type[ConfigField[Any]]],
) -> Parser[dict[str, Any]]:
    fields = {key: cls(key) for key, cls in fields_raw.items()}
    parse_line = terminated(line_parser(fields), cut(tag("\n")))

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
                fold(
                    parse_line,
                    fold_fn,
                    lambda: {name: [] for name in fields.keys()},
                ),
            ),
        )(s)

    return inner


class Config:
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
    tilemap_background_size: IVec2
    tilemap_background: list[list[ColoredLine]]
    tilemap_box_size: IVec2
    tilemap_box_bridge_size: IVec2
    tilemap_box: list[ColoredLine]
    prompt_size: IVec2
    prompt: list[ColoredLine]
    maze_pattern: list[str]

    def __init__(self) -> None:
        pass

    @staticmethod
    def parse(s: str) -> "Config":
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
                        ListParser(parse_colored_line),
                        [
                            '"{RED:BLACK}╔═╦╗"',
                            '"{RED:BLACK}║ ║║"',
                            '"{RED:BLACK}╠═╬╣"',
                            '"{RED:BLACK}╚═╩╝"',
                        ],
                    ),
                    "PROMPT_SIZE": DefaultedField(CoordField, IVec2(32, 5)),
                    "PROMPT": DefaultedStrField(
                        ListParser(parse_colored_line),
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
        if fields is None:
            raise ConfigException("Failed to parse config")
        res = Config()
        for key, val in fields[0].items():
            res.__dict__[key.lower()] = val

        if res.screensaver:
            res.visual = True

        return res
