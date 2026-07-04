from dataclasses import dataclass
from enum import Enum

class SongAction(Enum):
	PLAY = "play"
	EDIT = "edit"
	ADD_TO_PLAYLIST = "playlist"
	DELETE = "delete"

@dataclass
class SongMenuResult:
	action: SongAction
	payload: object | None = None