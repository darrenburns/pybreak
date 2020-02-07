import inspect
import pprint
import sys
import textwrap
import traceback
import types
from bdb import Bdb
from pathlib import Path

import pygments
from pygments.lexers.python import PythonLexer
from pygments.styles import get_style_by_name

from prompt_toolkit import PromptSession, print_formatted_text, HTML
from prompt_toolkit.application import run_in_terminal
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.formatted_text import PygmentsTokens
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles import Style, style_from_pygments_cls, merge_styles
from pybreak import __version__
from pybreak.command import Command, After, Quit, PrintNearbyCode
from pybreak.frame_history import FrameHistory
from pybreak.utility import get_terminal_size

styles = Style.from_dict({"rprompt": "gray"})

styles = merge_styles([
    styles,
    style_from_pygments_cls(get_style_by_name('monokai'))
])


def prompt_continuation(width, line_number, is_soft_wrap):
    continuation = '.' * (width - 1)
    return HTML(f"<green>{continuation}</green>")


class Pybreak(Bdb):
    def __init__(self):
        super().__init__()
        self.num_prompts = 0
        # self.frame_history.exec_frame: Optional[types.FrameType] = None
        # self.stack: List[inspect.Traceback] = []
        self.frame_history = FrameHistory()
        self.eval_count: int = 0
        self.prev_command = None

        bindings = KeyBindings()

        @bindings.add('c-n')
        def _(event: KeyPressEvent):
            buffer = event.current_buffer

            def do_next():
                cmd_name = "next"
                buffer.insert_text(cmd_name)
                Command.from_raw_input(cmd_name)
                buffer.validate_and_handle()

            run_in_terminal(do_next)

        @bindings.add("c-b")
        def _(event: KeyPressEvent):
            buffer = event.current_buffer

            def do_back():
                cmd_name = "back"
                buffer.insert_text(cmd_name)
                buffer.validate_and_handle()

            run_in_terminal(do_back)

        @bindings.add("c-f")
        def _(event: KeyPressEvent):
            buffer = event.current_buffer

            def do_forward():
                cmd_name = "forward"
                buffer.insert_text(cmd_name)
                buffer.validate_and_handle()

            run_in_terminal(do_forward)

        self.session = PromptSession(
            self._get_lprompt,
            lexer=PygmentsLexer(PythonLexer),
            rprompt=self._get_rprompt,
            style=styles,
            auto_suggest=AutoSuggestFromHistory(),
            multiline=True,
            bottom_toolbar=self._get_bottom_toolbar,
            prompt_continuation=prompt_continuation,
            key_bindings=bindings,
            input_processors={}
        )

    def repeatedly_prompt(self):
        if self.prev_command and self.prev_command.after == After.Proceed:
            PrintNearbyCode().run(self, self.frame_history.exec_frame)
        while True:
            self.num_prompts += 1
            try:
                input = self.session.prompt()
                if not input:
                    continue
            except KeyboardInterrupt:
                continue
            except EOFError:
                Quit().run(self, self.frame_history.exec_frame, ())
                break
            try:
                cmd, args = Command.from_raw_input(input)
            except KeyError:
                # The user entered text that doesn't correspond
                # to a standard command. Evaluate it.
                self._eval_and_print_result(input)
            else:
                cmd.run(self, self.frame_history.exec_frame, *args)
                if cmd.after == After.Proceed:
                    break
                elif cmd.after == After.Stay:
                    continue

    def _quit(self):
        sys.settrace(None)
        self.quitting = True

    def user_call(self, frame: types.FrameType, argument_list):
        pass

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
            self.frame_history.append(frame)
            # TODO: Only capture output if continuation command ran
            self.repeatedly_prompt()

    def start(self, frame):
        num_cols = get_terminal_size().cols
        if self.num_prompts < 1:
            print_formatted_text(HTML('_' * num_cols))
            print_formatted_text(HTML(f"<b>Pybreak {__version__}</b>\n"))
        super().set_trace(frame)

    def do_clear(self, arg):
        self.clear_all_breaks()

    def _get_rprompt(self):
        file_name = self.frame_history.exec_frame.filename
        line_no = self.frame_history.exec_frame.lineno
        try:
            rprompt = Path(file_name).relative_to(Path.cwd())
        except ValueError:
            rprompt = Path(file_name).stem

        return f"{rprompt}:{line_no}"

    def _get_bottom_toolbar(self):
        f = self.frame_history.exec_frame
        term_width = get_terminal_size().cols

        stack_size = len(self.frame_history.history)
        r_offset = stack_size - self.frame_history.hist_index
        if self.frame_history.viewing_history:
            mode_fg = "coral"
            mode_bg = "black"
            mode = f" Location: STACK[-{r_offset}] "
        else:
            mode_fg = "mediumseagreen"
            mode_bg = "white"
            mode = f" Location: STACK[-1] "

        mode_width = len(mode)

        content = f"Paused @ {Path(f.filename).stem}:{f.frame_info.function}:{f.lineno}"
        content = textwrap.shorten(content, width=term_width - mode_width - 2)
        content = f"{content:<{term_width - mode_width - 2}}"

        return HTML('<style fg="dodgerblue" bg="white"> {content} </style>'
                    '<style fg="{mode_fg}" bg="{mode_bg}">{mode}</style>').format(
            content=content,
            mode=mode,
            mode_fg=mode_fg,
            mode_bg=mode_bg,
        )

    def _eval_and_print_result(self, input: str):
        try:
            output = pprint.pformat(self.runeval(
                input, self.frame_history.exec_frame.frame_info.frame, self.frame_history.exec_frame.frame_locals
            ))
            tokens = pygments.lex(output, lexer=PythonLexer())
            print_formatted_text(PygmentsTokens(tokens))
        except Exception as err:
            self._print_exception(err)
        else:
            self.eval_count += 1

    def _print_exception(self, err):
        print_formatted_text("".join(traceback.format_exception_only(type(err), err)))

    def _get_lprompt(self):
        return HTML(f"<green>In [</green><b>{self.eval_count}</b><green>]</green>: ")


# You can only have a single instance of Pybreak alive at a time,
# because it depends on Bdb which uses class-level state.
# See python3.7/bdb.py:660
pb = Pybreak()


def set_trace():
    frame = inspect.currentframe().f_back
    pb.start(frame)
