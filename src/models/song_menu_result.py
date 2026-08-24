from dataclasses import dataclass
from enum import Enum

class SongAction(Enum):
	PLAY = "play"
	EDIT = "edit"
	UPDATE_TO_PLAYLIST = "playlist"
	DELETE = "delete"
	REMOVE = "remove"

@dataclass
class SongMenuResult:
	action: SongAction
	payload: object | None = None