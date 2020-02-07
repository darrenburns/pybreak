import types
from typing import Dict, Optional

from dataclasses import dataclass, field

from pybreak.frame_state import FrameState

FrameUUID = str


@dataclass
class StateManager:
    history: Dict[FrameUUID, FrameState] = field(default_factory=dict)
    location: Optional[FrameUUID] = None

    def append(self, frame: types.FrameType):
        """
        Append the frame to the history, and update
        the current location.
        """
        frame_state = FrameState(frame)
        self.location = frame_state.uuid
        self.history[self.location] = frame_state

    @property
    def current_frame(self) -> FrameState:
        """
        Retrieve the FrameState from the current
        location.
        """
        return self.history[self.location]
