import bdb
import inspect
import sys
import types
from enum import auto, Enum
from typing import Tuple

import pygments
from pygments.lexers.python import PythonLexer

from prompt_toolkit import print_formatted_text as log
from prompt_toolkit.formatted_text import PygmentsTokens
from pybreak.utility import get_file_lines


class After(Enum):
    Stay = auto()  # Stay still, we're just looking
    Proceed = auto()  # Moves us forward in the code


class Command:
    alias_list: Tuple[str] = ()
    after: After = After.Stay
    all = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        instance = cls()
        for alias in cls.alias_list:
            cls.all[alias] = instance

    def run(self, debugger: bdb.Bdb, frame: types.FrameType):
        raise NotImplementedError("Command.run must be implemented by subclasses.")

    @classmethod
    def from_alias(cls, input) -> "Command":
        return cls.all[input]


class PrintLocals(Command):
    alias_list = ("l", "locals")

    def run(self, debugger, frame):
        log(frame.f_locals)


class PrintArguments(Command):
    alias_list = ("a", "args")

    def run(self, debugger, frame):
        log(inspect.getargvalues(frame))


class Next(Command):
    alias_list = ("n", "next")
    after = After.Proceed

    def run(self, debugger, frame):
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

    def run(self, debugger, frame):
        debugger.set_continue()


class Quit(Command):
    alias_list = ("q", "quit")
    after = After.Proceed

    def run(self, debugger, frame):
        sys.settrace(None)
        debugger.quitting = True
