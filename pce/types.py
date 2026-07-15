"""Type definitions"""
import enum
from typing import Any, Dict, Union


class OutEvents(str, enum.Enum):
    phase = "phase"
    players = "players"
    meta = "meta"
    error = "error"


Event = Dict[str, Union[OutEvents, str, Dict[str, Any]]]
