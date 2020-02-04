import inspect
import sys
import types
from bdb import Bdb
from typing import Optional, Iterable

from dataclasses import dataclass
from pygments.lexers.python import PythonLexer

from prompt_toolkit import PromptSession
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout import BufferControl, Window, ScrollbarMargin, NumberedMargin, Container
from prompt_toolkit.lexers import PygmentsLexer


class Repl:
    def __init__(
        self,
        prompt: str = "> ",
    ):
        self.prompt = prompt
        self.buffer = Buffer(
            multiline=False,
        )
        self.control = BufferControl(
            buffer=self.buffer,
            lexer=PygmentsLexer(PythonLexer),
            focusable=True,
            focus_on_click=True,
        )
        self.window = Window(
            content=self.control,
            dont_extend_height=True,
            dont_extend_width=True,
            wrap_lines=True,
            right_margins=[ScrollbarMargin(display_arrows=True)],
            left_margins=[NumberedMargin()],  # TODO: Make margin indicate in/out nums
        )

    def __pt_container__(self) -> Container:
        return self.window


#####################################################
#                           #                       #
#                           #                       #
#                           #   Local variables     #
#                           #                       #
#   Source code             #                       #
#                           #                       #
#                           #########################
#                           #                       #
#                           #                       #
#                           #  Evaluate expression  #
#                           #                       #
#                           #                       #
#                           #                       #
#                           #                       #
#                           #                       #
#####################################################


@dataclass
class ActiveLine:
    file_name: str
    line_number: int


class Pybreak(Bdb):
    def __init__(
        self,
        skip: Optional[Iterable[str]] = None,
    ):
        super().__init__(skip=skip)
        self.skip = skip
        self.paused_at_line = False
        self.files_seen = []
        self.session = PromptSession()
        self.current_frame: Optional[types.FrameType] = None

    def repeatedly_prompt(self):
        while True:
            try:
                input = self.session.prompt("> ")
            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            else:
                print("You entered: ", input)
                if input == "n":
                    self.do_next(self.current_frame)
                    print(self.current_frame)
                    # "n" results in continuing execution
                    break
                if input == "q":
                    # Stop tracing and break out of prompt
                    self._quit()
                    # TODO: Temp disable stdout to hide bdbquit error?
                    #  doesn't seem to be catchable
                    break

    def _quit(self):
        sys.settrace(None)
        self.quitting = True

    def _print_current_frame(self):
        print(f"{self.current_frame.f_lineno} | {self.current_frame.f_code.co_filename}")

    def user_call(self, frame: types.FrameType, argument_list):
        fname = frame.f_code.co_filename
        lineno = frame.f_lineno

    def user_line(self, frame: types.FrameType):
        """
        This method is called from dispatch_line() when either
        stop_here() or break_here() yields True.
        i.e. when we stop OR break at this line.
         * stop_here() yields true if the frame lies below the frame where
         debugging started on the call stack. i.e. it will be called for
         every line after we start debugging.
         * break_here() yields true only if there's a breakpoint for this
         line
        """
        if self.stop_here(frame):
            # We're stopping at this frame, so update our internal
            # state.
            self.current_frame = frame
            self.repeatedly_prompt()

    def start(self, frame):
        super().set_trace(frame)
        self.current_frame = frame

    def do_continue(self):
        self.set_continue()

    def do_clear(self, arg):
        self.clear_all_breaks()

    def do_next(self, frame):
        self.set_next(frame)


# You can only have a single instance of Pybreak alive at a time,
# because it depends on Bdb which uses class-level state.
# See python3.7/bdb.py:660
pb = Pybreak()


def set_trace():
    frame = inspect.currentframe().f_back
    pb.start(frame)
