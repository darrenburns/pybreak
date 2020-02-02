from pygments.lexers.python import PythonLexer

from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout import BufferControl, Window, ScrollbarMargin, NumberedMargin, Container
from prompt_toolkit.lexers import PygmentsLexer


def python_completer(local_namespace, global_namespace):
    raise NotImplementedError()


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
