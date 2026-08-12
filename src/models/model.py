from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias

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
	file_path: str

@dataclass
class Node:
	parent: str
	name: str

class PlaylistAction(Enum):
	EDIT = "edit"
	DELETE = "delete"

@dataclass
class PlaylistMenuResult:
	action: PlaylistAction
	payload: object | None = None

# ============================================================
# AST nodes
# ============================================================

@dataclass
class Comparison:
    field: str
    operator: str
    value: str


@dataclass
class And:
    left: Expression
    right: Expression


@dataclass
class Or:
    left: Expression
    right: Expression

Expression: TypeAlias = Comparison | And | Or