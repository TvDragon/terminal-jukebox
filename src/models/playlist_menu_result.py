from dataclasses import dataclass
from enum import Enum

class PlaylistAction(Enum):
	EDIT = "edit"
	DELETE = "delete"

@dataclass
class PlaylistMenuResult:
	action: PlaylistAction
	payload: object | None = None