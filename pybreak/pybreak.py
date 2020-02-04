import functools
import inspect
import sys
import traceback
import types
from bdb import Bdb
from pathlib import Path
from typing import Optional, Iterable, Tuple

import pygments
from dataclasses import dataclass
from pygments.lexers.python import PythonLexer

from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.formatted_text import PygmentsTokens
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles import Style


@functools.lru_cache(8)
def get_file_lines(file_name: str) -> Tuple[str]:
    with open(file_name, "rb") as f:
        return tuple(line.decode("utf-8") for line in f.readlines())


@dataclass
class ActiveLine:
    file_name: str
    line_number: int


styles = Style.from_dict({
    'rprompt': 'gray',
})


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
        self.eval_count: int = 0

    def repeatedly_prompt(self):
        while True:
            try:
                input = self.session.prompt(
                    self._get_lprompt(),
                    lexer=PygmentsLexer(PythonLexer),
                    rprompt=self._get_rprompt(),
                    style=styles,
                    multiline=True,
                )
                print_formatted_text(input)
            except KeyboardInterrupt:
                continue
            except EOFError:
                print_formatted_text("eof")
                break
            else:
                if input == "n":
                    self.do_next(self.current_frame)
                    self._print_new_dest()
                    # "n" results in continuing execution
                    break
                elif input == "q":
                    # Stop tracing and break out of prompt
                    self._quit()
                    break
                elif input == "l":
                    self._print_locals()
                elif input == "a":
                    self._print_args()
                else:
                    # Command not recognised, so eval
                    print()
                    print_formatted_text("not recognised")
                    self._eval_and_print_result(input)

    def _quit(self):
        sys.settrace(None)
        self.quitting = True

    def _print_new_dest(self):
        file_name = self.current_frame.f_code.co_filename
        line_number = self.current_frame.f_lineno
        lines = get_file_lines(file_name)
        line = lines[line_number]
        output_line = f"{line_number} | {line}"
        tokens = list(pygments.lex(output_line, lexer=PythonLexer()))
        print_formatted_text(PygmentsTokens(tokens))
        # print(f"{self.current_frame.f_lineno} | {self.current_frame.f_code.co_filename}")

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
            # TODO: Only capture output if continuation command ran
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


    def current_file(self):
        pass


    def _get_rprompt(self):
        file_name = self.current_frame.f_code.co_filename
        line_no = self.current_frame.f_lineno
        try:
            rprompt = Path(file_name).relative_to(Path.cwd())
        except ValueError:
            rprompt = Path(file_name).stem

        return f"{rprompt}:{line_no}"


    def _print_locals(self):
        print_formatted_text(self.current_frame.f_locals)


    def _print_args(self):
        print_formatted_text(inspect.getargvalues(self.current_frame))


    def _eval_and_print_result(self, input: str):
        try:
            print_formatted_text(self.runeval(input, self.current_frame.f_globals, self.current_frame.f_locals))
        except Exception as err:
            self._print_exception(err)
        else:
            self.eval_count += 1


    def _print_exception(self, err):
        print_formatted_text("".join(traceback.format_exception_only(type(err), err)))


    def _get_lprompt(self):
        return f"[{self.eval_count}] "


# You can only have a single instance of Pybreak alive at a time,
# because it depends on Bdb which uses class-level state.
# See python3.7/bdb.py:660
pb = Pybreak()


def set_trace():
    frame = inspect.currentframe().f_back
    pb.start(frame)
