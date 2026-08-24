from dataclasses import dataclass

@dataclass
class SongPlaylists:
	playlist_id: int
	playlist_name: str
	song_id: int
	in_playlist: bool
	is_auto_playlist: bool