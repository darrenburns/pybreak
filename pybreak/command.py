import bdb
import inspect
import sys
import types
from enum import auto, Enum
from typing import Tuple, Dict, Any

import pygments
from pygments.lexers.python import PythonLexer

from prompt_toolkit import print_formatted_text as log
from prompt_toolkit.formatted_text import PygmentsTokens
from pybreak.utility import get_file_lines


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
    def from_alias(cls, input) -> "Command":
        return cls.all[input]

    def validate_args(self, called_with: Tuple[Any]):
        if len(called_with) != self.arity:
            log(
                f"{self.alias_list[0]} takes {self.arity} argument{'s' if self.arity != 1 else ''}, not {len(called_with)}."
            )


class PrintNearbyCode(Command):
    """
    .
    """
    alias_list = ("l", "line", "lines")

    def run(self, debugger, frame, *args):
        log(frame.f_locals)


class PrettyPrintValue(Command):
    """
    Pretty print a variable that is currently in scope.
    """
    alias_list = ("pp", "pretty", "pprint")
    arity = 1  # TODO: Use an ArgSpec instead of arity, could do optional args etc.

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
        file_name = frame.f_code.co_filename
        line_number = frame.f_lineno
        lines = get_file_lines(file_name)
        line = lines[line_number]
        output_line = f"{line_number} | {line}"
        tokens = list(pygments.lex(output_line, lexer=PythonLexer()))
        log(PygmentsTokens(tokens))


class Continue(Command):
    """
    Continue execution until the next break point.
    """
    alias_list = ("c", "cont", "continue")
    after = After.Proceed

    def run(self, debugger, frame, *args):
        debugger.set_continue()


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
