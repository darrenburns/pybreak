import argparse
import pathlib
from pygments.lexers.python import PythonLexer

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Window, FormattedTextControl, Layout, VSplit
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.output import ColorDepth
from prompt_toolkit.widgets import TextArea
from pybreak.repl import Repl


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

def handle_prompt_input(buf: Buffer):
    # buf.reset(append_to_history=True)
    # pdb.set_trace()
    return True


def build_application(
    file
):
    with file.open("r") as f:
        src_code = f.read()

    body = VSplit(
        [
            TextArea(
                src_code,
                line_numbers=True,
                read_only=True,
                lexer=PygmentsLexer(PythonLexer),
            ),
            Window(width=1, char="|"),
            HSplit(
                [
                    Window(FormattedTextControl("local vars here")),
                    Window(height=1, char="-"),
                    Repl(),
                ]
            ),
        ]
    )

    kb = KeyBindings()

    @kb.add("q")
    def _(event):
        event.app.exit()

    return Application(
        layout=Layout(body),
        key_bindings=kb,
        full_screen=True,
        mouse_support=True,
        color_depth=ColorDepth.TRUE_COLOR,
    )


def run():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('file', type=pathlib.Path)
    args = vars(parser.parse_args())
    file = args.get("file")
    app = build_application(file)
    app.run()
