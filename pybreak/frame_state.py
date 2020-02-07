import datetime
import inspect
import types
import uuid
from typing import Dict, Any

from dataclasses import dataclass


def frame_uuid():
    return uuid.uuid4().hex


@dataclass
class FrameState:
    def __init__(self, frame: types.FrameType):
        self.raw_frame = frame
        self.frame_info: inspect.Traceback = inspect.getframeinfo(frame)
        self.frame_locals: Dict[str, Any] = frame.f_locals
        self.uuid: str = frame_uuid()
        self.exec_time: datetime.datetime = datetime.datetime.now()

    @property
    def uuid_short(self):
        return uuid[:6]

    @property
    def filename(self) -> str:
        return self.frame_info.filename

    @property
    def lineno(self) -> int:
        return self.frame_info.lineno
