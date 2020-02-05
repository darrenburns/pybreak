import functools
import os

import pygments
from dataclasses import dataclass
from pygments.lexers.python import PythonLexer

from prompt_toolkit import HTML
from prompt_toolkit.formatted_text import PygmentsTokens, split_lines, to_formatted_text


def get_location_snippet(file_name: str, focus_line: int):
    line_idx = max(0, focus_line - 1)
    tokenised = get_tokenised_lines(file_name)
    snippet = make_snippet(tokenised, line_idx)
    return snippet


def make_snippet(tokenised_lines, focus_line_idx: int):
    lines_around = 5  # TODO make arg
    start_line_idx = max(focus_line_idx - lines_around, 0)
    end_line_idx = min(focus_line_idx + lines_around, len(tokenised_lines))
    snippet_lines = tokenised_lines[start_line_idx:end_line_idx]

    # We've trimmed the lines, so correct the line to focus on
    corrected_line_index = focus_line_idx - start_line_idx
    return with_gutter(snippet_lines, start_line_idx, corrected_line_index)


def formatted_padding(n):
    return 'class:pygments.text', (' ' * n)


def with_gutter(lines, start_line_idx: int, focus_line_idx: int):
    start_line_num = start_line_idx + 1
    g_width = len(str(start_line_num + len(lines)))
    updated_lines = []
    for i, line in enumerate(lines):
        line = line + [formatted_padding(2)]
        # TODO: Conditionally style the line,
        #  only if it's the active one.
        if i == focus_line_idx:
            bg = "bg:#313131 bold"
        else:
            bg = None

        if i == focus_line_idx:
            gutter_fg = "greenyellow"
        else:
            gutter_fg = "slategray"
        gutter_tokens = HTML(
            f"<span fg='{gutter_fg}'> {start_line_num + i:>{g_width}}  </span>  "
        ).formatted_text
        full_line = to_formatted_text(gutter_tokens + line, style=bg)
        updated_lines.append(full_line)

    return updated_lines


@functools.lru_cache(8)
def get_tokenised_lines(file_name: str):
    with open(file_name, "rb") as f:
        # We lex the enter file, otherwise things
        # like multiline strings will break syntax
        # highlighting when lines are trimmed.
        src = f.read()
        tokens = pygments.lex(src, lexer=PythonLexer())
        tokens = to_formatted_text(PygmentsTokens(tokens))
        return list(to_formatted_text(l) for l in split_lines(tokens))


@dataclass
class TerminalSize:
    rows: int
    cols: int


def get_terminal_size() -> TerminalSize:
    for i in range(0, 3):
        try:
            cols, rows = os.get_terminal_size(i)
            return TerminalSize(rows=rows, cols=cols)
        except OSError:
            continue
    return TerminalSize(rows=24, cols=80)
