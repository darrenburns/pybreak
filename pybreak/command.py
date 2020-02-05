import bdb
import inspect
import shlex
import sys
import types
from enum import auto, Enum
from typing import Tuple, Dict, Any, Sequence, Optional

import pygments
from pygments.lexers.python import PythonLexer

from prompt_toolkit import print_formatted_text as log
from prompt_toolkit.formatted_text import PygmentsTokens
from pybreak.utility import get_file_lines


def python_lines(
    lines: Sequence[str],
    starting_line_number: int,
    active_line: Optional[int] = None,
) -> PygmentsTokens:
    g_width = len(str(starting_line_number + len(lines)))
    gutter = " {:>{g_width}} {sep} {}"
    lines = [gutter.format(
        starting_line_number + i,
        line,
        g_width=g_width,
        sep=">" if starting_line_number + i == active_line else "|",
    ) for i, line in enumerate(lines)]
    src = "".join(lines)
    tokens = list(pygments.lex(src, lexer=PythonLexer()))
    tokens = PygmentsTokens(tokens)
    return tokens


class After(Enum):
    Stay = auto()  # Stay still, we're just looking
    Proceed = auto()  # Moves us forward in the code


Alias = str


class Command:
    alias_list: Tuple[Alias] = ()
    after: After = After.Stay
    arity: int = 0
    all: Dict[Alias, "Command"] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        instance = cls()
        for alias in cls.alias_list:
            cls.all[alias] = instance

    def run(
        self, debugger: bdb.Bdb, frame: types.FrameType, *args,
    ):
        raise NotImplementedError("Command.run must be implemented by subclasses.")

    @classmethod
    def from_raw_input(cls, input) -> Tuple["Command", Tuple[Any]]:
        parts = shlex.split(input)
        if len(parts) > 1:
            args = tuple(parts[1:])
        else:
            args = ()
        return cls.all[parts[0]], args

    def validate_args(self, called_with: Tuple[Any]):
        if len(called_with) != self.arity:
            log(
                f"{self.alias_list[0]} takes {self.arity} argument{'s' if self.arity != 1 else ''}, not {len(called_with)}."
            )


class PrintNearbyCode(Command):
    """
    Print the lines surrounding the current line.
    """

    alias_list = ("l", "line", "lines")
    LINES_BEFORE = 5
    LINES_AFTER = 5

    def run(self, debugger, frame, *args):
        # TODO, take the number of lines to show from
        #  the args rather than hardcoding
        lines = get_file_lines(frame.f_code.co_filename)
        line_no = frame.f_lineno
        from_index = max(line_no - self.LINES_BEFORE, 0)
        to_index = min(line_no + self.LINES_AFTER, len(lines))
        nearby = lines[from_index:to_index]
        from_line_number = from_index + 1
        log("")
        log(python_lines(nearby, from_line_number, line_no))


class PrettyPrintValue(Command):
    """
    Pretty print a variable that is currently in scope.
    """

    alias_list = ("pp", "pretty", "pprint")
    arity = 1

    def run(self, debugger, frame, *args):
        self.validate_args(args)


class PrintArguments(Command):
    """
    Print the arguments of the current function.
    """

    alias_list = ("a", "args")

    def run(self, debugger, frame, *args):
        log(inspect.getargvalues(frame))


class WatchVariable(Command):
    """
    Watch a variable visible in the current scope
    for changes. As you progress through code, you
    will be notified of any changes in the variable.
    """

    def run(self, debugger, frame, *args):
        pass

    alias_list = ("w", "watch")
    arity = 1


class DiffVariable(Command):
    """
    Show a diff between the current repr of a variable
    with the previous repr, before it last changed.
    """

    def run(self, debugger, frame, *args):
        pass

    alias_list = ("d", "diff")
    arity = 1


class NextLine(Command):
    """
    Continue execution until the next line.
    """

    alias_list = ("n", "next")
    after = After.Proceed

    def run(self, debugger, frame, *args):
        debugger.set_next(frame)
        PrintNearbyCode().run(debugger, frame)


class Continue(Command):
    """
    Continue execution until the next break point.
    """

    alias_list = ("c", "cont", "continue")
    after = After.Proceed

    def run(self, debugger, frame, *args):
        debugger.set_continue()
        PrintNearbyCode().run(debugger, frame)


class Quit(Command):
    """
    Quit Pybreak.
    """

    alias_list = ("q", "quit")
    after = After.Proceed

    def run(self, debugger, frame, *args):
        sys.settrace(None)
        debugger.quitting = True


class NextReturn(Command):
    """
    Continue execution until the current function returns.
    """

    alias_list = ("r", "return")
    after = After.Proceed

    def run(self, debugger, frame, *args):
        debugger.set_return(frame)


class Step(Command):
    """
    Execute the current line, but stop at the earliest possible
    moment. This could be in a function called on the current line,
    or perhaps on the next line.
    """

    alias_list = ("s", "step")

    def run(self, debugger, frame, *args):
        debugger.set_step()
