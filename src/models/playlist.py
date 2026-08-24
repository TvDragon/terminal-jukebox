from dataclasses import dataclass

@dataclass
class PlaylistInfo:
	id: int
	playlist_name: str
	is_auto_playlist: bool
	advanced_filter: str