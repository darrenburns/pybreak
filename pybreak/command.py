import bdb
import difflib
import pprint
import shlex
import textwrap
from enum import auto, Enum
from typing import Tuple, Dict, Any

import sys
from pygments.styles import get_style_by_name

from prompt_toolkit import print_formatted_text as log, HTML
from prompt_toolkit.styles import style_from_pygments_cls
from pybreak.frame_state import FrameState
from pybreak.utility import get_location_snippet, get_terminal_size

monokai = style_from_pygments_cls(get_style_by_name('monokai'))


class After(Enum):
    Stay = auto()  # Stay still, we're just looking
    Proceed = auto()  # For commands that increase the size of the stack, i.e. actually execute code


Alias = str


class Command:
    alias_list: Tuple[Alias] = ()
    after: After = After.Stay
    arity: int = 0
    all: Dict[Alias, "Command"] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        instance = cls()
        # TODO: Detect alias clashes between multiple commands
        for alias in cls.alias_list:
            cls.all[alias] = instance

    @classmethod
    def instance(cls):
        return cls.all[cls.alias_list[0]]

    def run(
        self, debugger: bdb.Bdb, frame: FrameState, *args,
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

    def run(self, debugger, frame, *args):
        # TODO, take the number of lines to show from
        #  the args rather than hardcoding
        file_name = debugger.frame_history.exec_frame.filename
        line_no = debugger.frame_history.exec_frame.lineno
        if debugger.frame_history.exec_frame.raw_frame is frame.raw_frame:
            secondary_line_no = debugger.frame_history.hist_frame.lineno
        else:
            secondary_line_no = -1
        lines = get_location_snippet(file_name, line_no, secondary_line_no)
        log("")
        for line in lines:
            log(line, style=monokai)
        log("")


class PrettyPrintValue(Command):
    """
    Pretty print a variable that is currently in scope.
    """

    alias_list = ("pp", "pretty", "pprint")
    arity = 1

    def run(self, debugger, frame, *args):
        self.validate_args(args)
        debugger.prev_command = self


class PrintArguments(Command):
    """
    Print the arguments of the current function.
    """

    alias_list = ("a", "args")

    def run(self, debugger, frame, *args):
        for var, val in frame.frame_locals.items():
            output = textwrap.shorten(f"{var} = {val}", get_terminal_size().cols - 2)
            log(output, style=monokai)
        debugger.prev_command = self


class WatchVariable(Command):
    """
    Watch a variable visible in the current scope
    for changes. As you progress through code, you
    will be notified of any changes in the variable.
    """

    def run(self, debugger, frame, *args):
        debugger.prev_command = self

    alias_list = ("w", "watch")
    arity = 1


class DiffVariable(Command):
    """
    Show a diff between the current repr of a variable
    with the previous repr, before it last changed.
    """
    alias_list = ("d", "diff")
    arity = 1

    def run(self, debugger, frame, *args):
        self.validate_args(args)
        exec_frame: FrameState = debugger.frame_history.exec_frame
        hist_frame: FrameState = debugger.frame_history.hist_frame
        var_name = args[0]

        # Lets ensure that we're in the same frame
        if hist_frame.raw_frame is exec_frame.raw_frame:
            hist_repr = pprint.pformat(hist_frame.frame_locals.get(var_name)).split('\n')
            exec_repr = pprint.pformat(exec_frame.frame_locals.get(var_name)).split('\n')
            differ = difflib.Differ()
            diff = differ.compare(hist_repr, exec_repr)
            colour_diff = []
            offset = debugger.frame_history.hist_offset
            for line in diff:
                if line.startswith("+"):
                    # Exec frame value
                    colour_diff.append(
                        f"<style bg='greenyellow' fg='black'> {var_name} @ STACK[-1] </style> <greenyellow>{line[1:]}</greenyellow>")
                elif line.startswith("-"):
                    # Historical frame value
                    colour_diff.append(
                        f"<style bg='coral' fg='black'> {var_name} @ STACK[-{offset}] </style> <coral>{line[1:]}</coral>")
                else:
                    colour_diff.append(f"{' ' * (14 + len(var_name) + len(str(offset)))}{line[1:]}")
            log(HTML("\n".join(colour_diff)))

        debugger.prev_command = self


class HistoryOfVariable(Command):
    """
    List all the historical changes to a variable
    currently in scope. TODO: In scope where? Orange or green?
    """
    alias_list = ("h", "hist", "history")
    arity = 1

    def run(self, debugger, frame, *args):
        self.validate_args(args)
        frames = debugger.frame_history
        hist = frames.history_of_local(args[0])
        log(hist)


class NextLine(Command):
    """
    Continue execution until the next line.
    """

    alias_list = ("n", "next")
    after = After.Proceed

    def run(self, debugger, frame, *args):
        debugger.set_next(frame.raw_frame)
        debugger.prev_command = self


class Back(Command):
    alias_list = ("b", "back")
    after = After.Stay  # length of stack remains same

    def run(self, debugger, frame, *args):
        previous_frame = debugger.frame_history.rewind()
        PrintNearbyCode.instance().run(debugger, previous_frame)


class Forward(Command):
    alias_list = ("f", "forward")
    after = After.Stay

    def run(self, debugger, frame, *args):
        next_frame = debugger.frame_history.forward()
        PrintNearbyCode.instance().run(debugger, next_frame)


class Continue(Command):
    """
    Continue execution until the next break point.
    """

    alias_list = ("c", "cont", "continue")
    after = After.Proceed

    def run(self, debugger, frame, *args):
        debugger.set_continue()
        debugger.prev_command = self


class Quit(Command):
    """
    Quit Pybreak.
    """

    alias_list = ("q", "quit")
    after = After.Proceed

    def run(self, debugger, frame, *args):
        sys.settrace(None)
        debugger.prev_command = self
        debugger.quitting = True


class NextReturn(Command):
    """
    Continue execution until the current function returns.
    """

    alias_list = ("r", "return")
    after = After.Proceed

    def run(self, debugger, frame, *args):
        debugger.set_return(frame.raw_frame)
        debugger.prev_command = self


class Step(Command):
    """
    Execute the current line, but stop at the earliest possible
    moment. This could be in a function called on the current line,
    or perhaps on the next line.
    """
    after = After.Proceed
    alias_list = ("s", "step")

    def run(self, debugger, frame, *args):
        debugger.set_step()
        debugger.prev_command = self
