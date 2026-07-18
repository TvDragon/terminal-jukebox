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

@dataclass
class SongPlaylists:
	playlist_id: int
	playlist_name: str
	song_id: int
	in_playlist: bool
	is_auto_playlist: bool

@dataclass
class SongInfo:
	id:	int
	title:	str
	artist:	str
	album:	str
	genres:	str