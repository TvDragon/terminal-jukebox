from dataclasses import dataclass

@dataclass
class SongInfo:
	id:	int
	title:	str
	artist:	str
	album:	str
	genres:	str
	duration_ms: int
	file_path: str