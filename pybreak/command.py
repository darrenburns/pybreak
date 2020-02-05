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

    def bad_arity(self, called_with: Tuple[Any]):
        log(
            f"{self.alias_list[0]} takes {self.arity} argument{'s' if self.arity != 1 else ''}, not {len(called_with)}."
        )


class PrintLocals(Command):
    alias_list = ("l", "locals")

    def run(self, debugger, frame, *args):
        log(frame.f_locals)


class PrettyPrintValue(Command):
    alias_list = ("pp", "pretty", "prettify")
    arity = 1

    def run(self, debugger, frame, *args):
        if len(args) != 1:
            self.bad_arity(args)
        log("Not yet implemented")


class PrintArguments(Command):
    alias_list = ("a", "args")

    def run(self, debugger, frame, *args):
        log(inspect.getargvalues(frame))


class Next(Command):
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
    alias_list = ("c", "cont", "continue")
    after = After.Proceed

    def run(self, debugger, frame, *args):
        debugger.set_continue()


class Quit(Command):
    alias_list = ("q", "quit")
    after = After.Proceed

    def run(self, debugger, frame, *args):
        sys.settrace(None)
        debugger.quitting = True
