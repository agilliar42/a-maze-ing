from collections.abc import Callable
from typing import Any
import textwrap

from mazegen.utils.ivec2 import IVec2


type ParseResult[T] = tuple[T, str] | ParseError
type Parser[T] = Callable[[str], ParseResult[T]]


class ParseError(Exception):
    """
    A parser error, with a message, location information, and subcauses
    Provides convenient ways to format the error for reporting
    """

    def __init__(
        self, msg: str, at: str, caused_by: list["ParseError"] | None = None
    ) -> None:
        self.msg: str = msg
        self.at: str = at
        self.caused_by: list[ParseError] | None = caused_by
        super().__init__(
            f"{msg}\nat: {at[:40]}\n" + f"subcauses:\n{self.caused_by}"
        )

    def get_text_pos(self, input_str: str) -> IVec2:
        """
        Returns the position of the error as one-indexed row and column,
        from the given input text
        """
        pred_len = len(input_str) - len(self.at)
        row = input_str.count("\n", 0, pred_len) + 1
        column = pred_len - max(input_str.rfind("\n", 0, pred_len), 0)
        return IVec2(column, row)

    def get_line(self, input_str: str) -> str:
        """
        Returns the line where this error occured, from the input str
        """
        pred_len = len(input_str) - len(self.at)
        line_start = input_str.rfind("\n", 0, pred_len) + 1
        line_end = max(input_str.find("\n", pred_len), 0)
        return input_str[line_start:line_end]

    def pretty_format(self, input_str: str, filename: str) -> str:
        """
        Returns a string containing the formatted error message, with
        subcause information, convenient position indication, and subcauses

        The style is roughly taken from rustc error messages
        """
        pos = self.get_text_pos(input_str)
        col = pos.x
        row = pos.y
        num_str = f"{row} "
        space_pad_str = " " * len(num_str)
        pad_str = space_pad_str + "|"
        suberrors = (
            []
            if self.caused_by is None
            else [
                textwrap.indent(
                    e.pretty_format(input_str, filename), pad_str + " "
                )
                + f"{pad_str}\n"
                for e in self.caused_by
            ]
        )
        return (
            f" --> {filename}:{row}:{col}\n"
            + f"{pad_str}\n"
            + f"{num_str}| {self.get_line(input_str)}\n"
            + f"{pad_str}{" " * col}^ {self.msg}\n"
            + f"{pad_str}\n"
            + f"{pad_str}\n".join(suberrors)
        )


def result_map[T, R](
    f: Callable[[T], R], res: T | ParseError
) -> R | ParseError:
    """
    Applies the given function to the result type if it is not an error
    Returns the mapped result
    """
    return f(res) if not isinstance(res, ParseError) else res


def parser_map[T, M](m: Callable[[T], M], p: Parser[T]) -> Parser[M]:
    """
    Like result, but composed with the given parser, such that output is
    mapped
    """
    return lambda s: result_map(lambda res: (m(res[0]), res[1]), p(s))


def parser_map_err[T](
    m: Callable[[ParseError], ParseError], p: Parser[T]
) -> Parser[T]:
    """
    Maps the parser to a parser where the error case has been mapped by m
    """
    return lambda s: (
        res
        if not isinstance(
            res := p(s),
            ParseError,
        )
        else m(res)
    )


def parser_default[T](p: Parser[T], default: T) -> Parser[T]:
    """
    Makes a parser infallible by giving a default value if it fails
    """
    return alt(p, value(default, null_parser))


def parser_complete[T](
    p: Parser[T],
) -> Parser[T]:
    """
    Makes the parser require for it to reach end of file
    """
    return terminated(p, eof_parser())


def recognize[T](p: Parser[T]) -> Parser[str]:
    """
    Maps any parser to a parser that returns as a value the consumed string
    """
    return lambda s: result_map(
        lambda rem: (s[: len(s) - len(rem[1])], rem[1]),
        p(s),
    )


def cut[T](p: Parser[T]) -> Parser[T]:
    """
    Makes the parser fail through exception when it fails through a value
    """

    def inner(s: str) -> ParseResult[T]:
        res: ParseResult[T] = p(s)
        if isinstance(res, ParseError):
            raise res
        return res

    return inner


def tag(tag: str) -> Parser[str]:
    """
    A parser that expects exactly the given string as input, then consumes
    and returns it
    """
    return lambda s: (
        (s[: len(tag)], s[len(tag) :])  # noqa E203
        if s.startswith(tag)
        else ParseError(f"Expected tag {repr(tag)}", s)
    )


def char(s: str) -> ParseResult[str]:
    """
    A parser that consumes one character
    """
    return (s[0], s[1:]) if len(s) > 0 else ParseError("Early EOF", s)


def null_parser(s: str) -> ParseResult[str]:
    """
    An infallible parser that matches and consumes zero characters
    """
    return ("", s)


def lookahead_parser[T, U](p1: Parser[T], p2: Parser[U]) -> Parser[T]:
    """
    Uses the first parser, and checks that the second parser succeeds to
    return a success, without having said second parser consume its input
    """

    def inner(s: str) -> ParseResult[T]:
        res = p1(s)
        if isinstance(res, ParseError):
            return res
        res2 = p2(res[1])
        if isinstance(res2, ParseError):
            return res2
        return res

    return inner


def eof_parser() -> Parser[str]:
    """
    A parser that expects end of file, that is an empty string
    """
    return lambda s: (
        ("", "") if len(s) == 0 else ParseError("Expected EOF", s)
    )


def nonempty_parser[T](p: Parser[T]) -> Parser[T]:
    """
    Takes a parser and only runs it if the input string is nonempty, otherwise
    errors
    """
    return lambda s: p(s) if len(s) > 0 else ParseError("Early EOF", s)


def value[T, V](val: V, p: Parser[T]) -> Parser[V]:
    """
    Maps the given parser to always return val instead
    """
    return parser_map(lambda _: val, p)


def alt[T](*choices: Parser[T]) -> Parser[T]:
    """
    A parser that returns the first of choices that matches
    Returns an error containing as subcauses all the parser's errors when
    no parser matches
    """

    def inner(s: str) -> ParseResult[T]:
        acc: list[ParseError] = []
        for e in map(lambda p: p(s), choices):
            if not isinstance(e, ParseError):
                return e
            acc.append(e)
        return ParseError("Expected any of the following to match:", s, acc)

    return inner


def fold[T, R](
    p: Parser[T],
    f: Callable[[R, T], R],
    acc_init: Callable[[], R],
    min_n: int = 0,
    max_n: int | None = None,
    sep: Parser[Any] = null_parser,
) -> Parser[R]:
    """
    Folds the given parser, interspered with sep, into accumulator, with at
    least min_n elements, and stops when max_n is reached
    """

    # no clean way to do this with lambdas i could figure out :<
    def inner(s: str) -> ParseResult[R]:
        curr_s = s
        acc = acc_init()
        count: int = 0
        curr_p: Parser[T] = p
        while max_n is None or count < max_n:
            nxt: ParseResult[T] = curr_p(curr_s)
            if isinstance(nxt, ParseError):
                if count < min_n:
                    return nxt
                break
            if count == 0:
                curr_p = preceeded(sep, p)
            count += 1
            acc = f(acc, nxt[0])
            curr_s = nxt[1]
        return (acc, curr_s)

    return inner


def many[T](
    p: Parser[T],
    min_n: int = 0,
    max_n: int | None = None,
    sep: Parser[Any] = null_parser,
) -> Parser[list[T]]:
    """
    Folds the given parser, interspered with sep, into a list of at least
    min_n elements, and stops when max_n is reached
    """
    return fold(
        parser_map(lambda e: [e], p),
        list.__add__,
        lambda: [],
        min_n,
        max_n,
        sep,
    )


def many_count[T](
    p: Parser[T],
    min_n: int = 0,
    max_n: int | None = None,
    sep: Parser[Any] = null_parser,
) -> Parser[int]:
    """
    Folds the given parser, interspered with sep, into a count of parses,
    with at least min_n elements, and stops when max_n is reached
    """
    return fold(value(1, p), int.__add__, lambda: 0, min_n, max_n, sep)


def seq[T](*parsers: Parser[T]) -> Parser[str]:
    """
    Applies the given parsers in succession, then returns the consumed string
    """

    def inner(s: str) -> ParseResult[None]:
        for parser in parsers:
            res = parser(s)
            if isinstance(res, ParseError):
                return res
            s = res[1]
        return (None, s)

    return recognize(inner)


def pair[T, U](p1: Parser[T], p2: Parser[U]) -> Parser[tuple[T, U]]:
    """
    Applies both parsers, returning a tuple of the two values if both succeed,
    or the first error it encounters
    """
    return lambda s: result_map(
        lambda res1: parser_map(lambda res2: (res1[0], res2), p2)(res1[1]),
        p1(s),
    )


def preceeded[_T0, T1](p1: Parser[_T0], p2: Parser[T1]) -> Parser[T1]:
    """
    Applies the parsers in succession then returns the value of p2
    """
    return parser_map(lambda res: res[1], pair(p1, p2))


def terminated[T0, _T1](p1: Parser[T0], p2: Parser[_T1]) -> Parser[T0]:
    """
    Applies the parsers in succession then returns the value of p1
    """
    return parser_map(lambda res: res[0], pair(p1, p2))


def delimited[_T0, T1, _T2](
    p1: Parser[_T0], p2: Parser[T1], p3: Parser[_T2]
) -> Parser[T1]:
    """
    Applies the parsers in succession then returns the value of p2
    """
    return preceeded(p1, terminated(p2, p3))


def one_of(chars: str) -> Parser[str]:
    """
    Parses exactly one character, if it is within chars
    """
    return parser_map_err(
        lambda s: ParseError(f"Expected one char of {repr(chars)}", s.at),
        alt(
            *map(tag, chars),
        ),
    )


def none_of(chars: str) -> Parser[str]:
    """
    Parses exactly one character, if it is not within chars
    """
    return lambda s: (
        char(s)
        if isinstance(one_of(chars)(s), ParseError)
        else ParseError(f"Expected any character except {repr(chars)}", s)
    )


def ascii_hexdigit(s: str) -> ParseResult[str]:
    """
    Parses one ascii hexadecimal character
    """
    return one_of("0123456789abcdefABCDEF")(s)


def ascii_digit(s: str) -> ParseResult[str]:
    """
    Parses one ascii decimal character
    """
    return one_of("0123456789")(s)
