from collections.abc import Callable
from typing import Any, cast


type ParseResult[T] = tuple[T, str] | None
type Parser[T] = Callable[[str], ParseResult[T]]


class ParseError(Exception):
    def __init__(self, msg: str, at: str) -> None:
        self.msg: str = msg
        self.at: str = at
        super().__init__(f"{msg}\n\nat: {at[:40]}")


def option_map[T, R](f: Callable[[T], R], val: T | None) -> R | None:
    return f(val) if val is not None else None


def parser_map[T, M](m: Callable[[T], M], p: Parser[T]) -> Parser[M]:
    return lambda s: option_map(lambda res: (m(res[0]), res[1]), p(s))


def parser_flatten[T](p: Parser[T | None]) -> Parser[T]:
    return lambda s: option_map(
        lambda res: cast(tuple[T, str], res) if res[0] is not None else None,
        p(s),
    )


def parser_default[T](p: Parser[T], default: T) -> Parser[T]:
    return alt(p, value(default, null_parser))


def parser_complete[T](p: Parser[T]) -> Parser[T]:
    def inner(res: tuple[T, str]) -> ParseResult[T]:
        if len(res[1]) != 0:
            raise ParseError(
                "Complete parser still had leftover characters to process",
                res[1],
            )
        return res

    return lambda s: option_map(inner, p(s))


def recognize[T](p: Parser[T]) -> Parser[str]:
    return lambda s: option_map(
        lambda rem: (s[: len(s) - len(rem[1])], rem[1]),
        p(s),
    )


def cut[T](p: Parser[T]) -> Parser[T]:
    def inner(s: str) -> ParseResult[T]:
        res: ParseResult[T] = p(s)
        if res is None:
            raise ParseError("Cut error: parser did not complete", s)
        return res

    return inner


def tag(tag: str) -> Parser[str]:
    return lambda s: (
        (s[: len(tag)], s[len(tag) :]) if s.startswith(tag) else None
    )


def char(s: str) -> ParseResult[str]:
    return (s[0], s[1:]) if len(s) > 0 else None


def null_parser(s: str) -> ParseResult[str]:
    return ("", s)


def value[T, V](val: V, p: Parser[T]) -> Parser[V]:
    return parser_map(lambda _: val, p)


def alt[T](*choices: Parser[T]) -> Parser[T]:
    return lambda s: next(
        filter(
            lambda e: e is not None,
            map(lambda p: p(s), choices),
        ),
        None,
    )


def fold[T, R](
    p: Parser[T],
    f: Callable[[R, T], R],
    acc: R,
    min_n: int = 0,
    max_n: int | None = None,
    sep: Parser[Any] = null_parser,
) -> Parser[R]:
    # no clean way to do this with lambdas i could figure out :<
    def inner(s: str) -> ParseResult[R]:
        nonlocal acc
        count: int = 0
        curr_p: Parser[T] = p
        while max_n is None or count < max_n:
            next: ParseResult[T] = curr_p(s)
            if next is None:
                break
            if count == 0:
                curr_p = preceeded(sep, p)
            count += 1
            acc = f(acc, next[0])
            s = next[1]
        return (acc, s) if count >= min_n else None

    return inner


def many[T](
    p: Parser[T],
    min_n: int = 0,
    max_n: int | None = None,
    sep: Parser[Any] = null_parser,
) -> Parser[list[T]]:
    return fold(
        parser_map(lambda e: [e], p), list.__add__, [], min_n, max_n, sep
    )


def many_count[T](
    p: Parser[T],
    min_n: int = 0,
    max_n: int | None = None,
    sep: Parser[Any] = null_parser,
) -> Parser[int]:
    return fold(value(1, p), int.__add__, 0, min_n, max_n, sep)


def seq[T](*parsers: Parser[T]) -> Parser[str]:
    def inner(s: str) -> ParseResult[None]:
        for parser in parsers:
            res = parser(s)
            if res is None:
                return None
            s = res[1]
        return (None, s)

    return recognize(inner)


def pair[T, U](p1: Parser[T], p2: Parser[U]) -> Parser[tuple[T, U]]:
    return lambda s: option_map(
        lambda res1: parser_map(lambda res2: (res1[0], res2), p2)(res1[1]),
        p1(s),
    )


def preceeded[_T0, T1](p1: Parser[_T0], p2: Parser[T1]) -> Parser[T1]:
    return parser_map(lambda res: res[1], pair(p1, p2))


def terminated[T0, _T1](p1: Parser[T0], p2: Parser[_T1]) -> Parser[T0]:
    return parser_map(lambda res: res[0], pair(p1, p2))


def delimited[_T0, T1, _T2](
    p1: Parser[_T0], p2: Parser[T1], p3: Parser[_T2]
) -> Parser[T1]:
    return preceeded(p1, terminated(p2, p3))


def one_of(chars: str) -> Parser[str]:
    return alt(*map(tag, chars))


def none_of(chars: str) -> Parser[str]:
    return lambda s: char(s) if one_of(chars)(s) is None else None


def ascii_hexdigit(s: str) -> ParseResult[str]:
    return one_of("0123456789abcdefABCDEF")(s)


def ascii_digit(s: str) -> ParseResult[str]:
    return one_of("0123456789")(s)
