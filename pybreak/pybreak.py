import inspect
from bdb import Bdb


class Pybreak(Bdb):
    def __init__(self, stdin=None, stdout=None, skip=None):
        super().__init__(skip=skip)
        self.stdin = stdin
        self.stdout = stdout
        self.skip = skip


def set_trace():
    dbg = Pybreak()
    dbg.set_trace(inspect.currentframe().f_back)
