from dataclasses import dataclass

@dataclass
class MusicFoldersInfo:
	id: int
	folder_path: str
	is_checked: int