from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, Type
from .parser_combinator import (
    ParseResult,
    Parser,
    alt,
    ascii_digit,
    cut,
    delimited,
    fold,
    many_count,
    none_of,
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


def parse_space(s: str) -> ParseResult[str]:
    return recognize(many_count(one_of(" \t")))(s)


def parse_comment(s: str) -> ParseResult[str]:
    return recognize(seq(tag("#"), many_count(none_of("\n"))))(s)


def parse_coord(s: str) -> ParseResult[tuple[int, int]]:
    return pair(
        terminated(
            parse_int,
            delimited(parse_space, tag(","), parse_space),
        ),
        parse_int,
    )(s)


def parse_path(s: str) -> ParseResult[str]:
    return recognize(many_count(none_of("\n"), min_n=1))(s)


class ConfigException(Exception):
    pass


class ConfigField[T](ABC):
    def __init__(
        self, name: str, default: Callable[[], T] | None = None
    ) -> None:
        self.__name = name
        self.__default = default

    @abstractmethod
    def parse(self, s: str) -> ParseResult[T]: ...

    def default(self) -> T:
        if self.__default is None:
            raise ConfigException(
                "Value "
                + self.__name
                + " not provided, and no default value exists"
            )
        return self.__default()

    def merge(self, vals: list[T]) -> T:
        if len(vals) == 0:
            return self.default()
        if len(vals) == 1:
            return vals[0]
        raise ConfigException(
            "More than one definition of config field " + self.__name
        )

    def name(self) -> str:
        return self.__name


class IntField(ConfigField[int]):
    def parse(self, s: str) -> ParseResult[int]:
        return parse_int(s)


class BoolField(ConfigField[bool]):
    def parse(self, s: str) -> ParseResult[bool]:
        return parse_bool(s)


class CoordField(ConfigField[tuple[int, int]]):
    def parse(self, s: str) -> ParseResult[tuple[int, int]]:
        return parse_coord(s)


class PathField(ConfigField[str]):
    def parse(self, s: str) -> ParseResult[str]:
        return parse_path(s)


def OptionalField[T](cls: Type[ConfigField[T]]) -> Type[ConfigField[T | None]]:
    class Inner(ConfigField[T | None]):
        parse = cls.parse

    return DefaultedField(Inner, None)


def DefaultedField[T](
    cls: Type[ConfigField[T]], default: T
) -> Type[ConfigField[T]]:
    class Inner(ConfigField[T]):
        def __init__(
            self,
            name: str,
            default: Callable[[], T] = lambda: default,
        ) -> None:
            super().__init__(name, default)

        parse = cls.parse

    return Inner


def line_parser[T](
    fields: dict[str, ConfigField[T]],
) -> Parser[tuple[str, T] | None]:
    return alt(
        parser_map(lambda _: None, parse_comment),
        *(
            preceeded(
                seq(tag(name), parse_space, tag("="), parse_space),
                parser_map(
                    (lambda name: lambda res: (name, res))(name),
                    cut(field.parse),
                ),
            )
            for name, field in fields.items()
        ),
    )


def fields_parser(
    fields_raw: dict[str, type[ConfigField]],
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
        return parser_map(
            fields_map,
            fold(
                parse_line,
                fold_fn,
                {name: [] for name in fields.keys()},
            ),
        )(s)

    return inner


class Config:
    width: int
    height: int
    entry: tuple[int, int] | None
    exit: tuple[int, int] | None
    output_file: str | None
    perfect: bool
    seed: int | None
    screensaver: bool
    visual: bool
    interactive: bool

    def __init__(self) -> None:
        pass

    @staticmethod
    def parse(s: str) -> "Config":
        fields = parser_complete(
            fields_parser(
                {
                    "WIDTH": IntField,
                    "HEIGHT": IntField,
                    "ENTRY": OptionalField(CoordField),
                    "EXIT": OptionalField(CoordField),
                    "OUTPUT_FILE": OptionalField(PathField),
                    "PERFECT": DefaultedField(BoolField, True),
                    "SEED": OptionalField(IntField),
                    "SCREENSAVER": DefaultedField(BoolField, False),
                    "VISUAL": DefaultedField(BoolField, False),
                    "INTERACTIVE": DefaultedField(BoolField, False),
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
