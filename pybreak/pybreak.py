import inspect
import sys
import textwrap
import traceback
import types
from bdb import Bdb
from pathlib import Path
from typing import Optional, Iterable

from dataclasses import dataclass
from pybreak import __version__
from pybreak.command import Command, After, Quit, PrintNearbyCode
from pybreak.utility import get_terminal_size
from pygments.lexers.python import PythonLexer

from prompt_toolkit import PromptSession, print_formatted_text, HTML
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles import Style


@dataclass
class ActiveLine:
    file_name: str
    line_number: int


styles = Style.from_dict({"rprompt": "gray", })


class Pybreak(Bdb):
    def __init__(
        self, skip: Optional[Iterable[str]] = None,
    ):
        super().__init__(skip=skip)
        self.num_prompts = 0
        self.skip = skip
        self.paused_at_line = False
        self.files_seen = []
        self.session = PromptSession(
            self._get_lprompt,
            lexer=PygmentsLexer(PythonLexer),
            rprompt=self._get_rprompt,
            style=styles,
            auto_suggest=AutoSuggestFromHistory(),
            multiline=True,
            bottom_toolbar=self._get_bottom_toolbar,
        )
        self.current_frame: Optional[types.FrameType] = None
        self.eval_count: int = 0
        self.prev_command = None

    def repeatedly_prompt(self):
        if self.prev_command and self.prev_command.after == After.Proceed:
            PrintNearbyCode().run(self, self.current_frame)
        while True:

            self.num_prompts += 1
            try:
                input = self.session.prompt()
                if not input:
                    continue
            except KeyboardInterrupt:
                continue
            except EOFError:
                Quit().run(self, self.current_frame, ())
                break

            try:
                cmd, args = Command.from_raw_input(input)
            except KeyError:
                # The user entered text that doesn't correspond
                # to a standard command. Evaluate it.
                self._eval_and_print_result(input)
            else:
                cmd.run(self, self.current_frame, *args)
                self.prev_command = cmd
                if cmd.after == After.Proceed:
                    break
                elif cmd.after == After.Stay:
                    continue

    def _quit(self):
        sys.settrace(None)
        self.quitting = True

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
        num_cols = get_terminal_size().cols
        if self.num_prompts < 1:
            print_formatted_text(HTML('_' * num_cols))
            print_formatted_text(HTML(f"<b>Pybreak v{__version__}</b>\n"))
        super().set_trace(frame)
        self.current_frame = frame

    def do_clear(self, arg):
        self.clear_all_breaks()

    def _get_rprompt(self):
        file_name = self.current_frame.f_code.co_filename
        line_no = self.current_frame.f_lineno
        try:
            rprompt = Path(file_name).relative_to(Path.cwd())
        except ValueError:
            rprompt = Path(file_name).stem

        return f"{rprompt}:{line_no}"

    def _get_bottom_toolbar(self):
        frameinfo = inspect.getframeinfo(self.current_frame)
        args = inspect.getargvalues(self.current_frame)
        term_width = get_terminal_size().cols
        content = f" in {Path(frameinfo.filename).stem}:{frameinfo.function}:{frameinfo.lineno} {args.locals}"

        content = textwrap.shorten(content, width=term_width - 1)
        content = f"{content:<{term_width}}"

        return HTML(f'<style fg="dodgerblue" bg="white">{content}</style>!')

    def _eval_and_print_result(self, input: str):
        try:
            print_formatted_text(
                self.runeval(
                    input, self.current_frame.f_globals, self.current_frame.f_locals
                )
            )
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
