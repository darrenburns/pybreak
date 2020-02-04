from enum import auto, Enum
from typing import List

from dataclasses import dataclass, field


class CommandCategory(Enum):
    Inspect = auto()  # Stay still, we're just looking
    Proceed = auto()  # Moves us forward in the code


@dataclass
class Command:
    alias_list: List[str] = field(default_factory=list)
    category: CommandCategory = CommandCategory.Inspect

    def run(self):
        raise NotImplementedError("Command.run must be implemented by subclasses.")


class PrintLocals(Command):
    def run(self):
        pass

