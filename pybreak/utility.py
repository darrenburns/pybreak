import functools
import os

import pygments
from dataclasses import dataclass
from pygments.lexers.python import PythonLexer

from prompt_toolkit import HTML
from prompt_toolkit.formatted_text import PygmentsTokens, split_lines, to_formatted_text, fragment_list_len


def get_location_snippet(file_name: str, focus_line: int, secondary_focus_line: int):
    line_idx = max(0, focus_line - 1)
    secondary_line_idx = max(0, secondary_focus_line - 1)
    tokenised = get_tokenised_lines(file_name)
    snippet = make_snippet(tokenised, line_idx, secondary_line_idx)
    return snippet


def make_snippet(tokenised_lines, focus_line_idx: int, secondary_focus_line_idx: int):
    lines_around = 5  # TODO make arg
    start_line_idx = max(focus_line_idx - lines_around, 0)
    end_line_idx = min(focus_line_idx + lines_around + 1, len(tokenised_lines))
    snippet_lines = tokenised_lines[start_line_idx:end_line_idx]

    # We've trimmed the lines, so correct the line to focus on
    corrected_line_index = focus_line_idx - start_line_idx
    corrected_secondary_line_index = secondary_focus_line_idx - start_line_idx
    return with_gutter(snippet_lines, start_line_idx, corrected_line_index, corrected_secondary_line_index)


def formatted_padding(n):
    return 'class:pygments.text', (" " * n)


def with_gutter(lines, start_line_idx: int, focus_line_idx: int, secondary_focus_idx: int):
    start_line_num = start_line_idx + 1
    updated_lines = []
    gutter_padding = 5  # Not ideal manually maintaining this
    term_width = get_terminal_size().cols
    for i, line in enumerate(lines):
        max_line_number_width = len(str(start_line_num + len(lines)))
        g_width = max_line_number_width + gutter_padding
        rpad_amount = term_width - g_width - fragment_list_len(line)
        line = line + [formatted_padding(rpad_amount)]
        if i == focus_line_idx:
            bg = "bg:#313131 bold"
            gutter_fg = "greenyellow"
        elif i == secondary_focus_idx and focus_line_idx != secondary_focus_idx:
            bg = "bg:#313131 bold"
            gutter_fg = "coral"
        else:
            bg = None
            gutter_fg = "slategray"

        gutter_tokens = to_formatted_text(HTML(
            f"<span fg='{gutter_fg}'> {start_line_num + i:>{max_line_number_width}}  </span>  "
        ))
        line = to_formatted_text(line)
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
        return list(l for l in split_lines(tokens))


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
