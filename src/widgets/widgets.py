from textual.app import ComposeResult
from textual.widgets import (
	Button,
	DataTable,
	Static,
)

# --- Music Table View --------------------------------------------------------

class MusicTable(DataTable):

	def on_mount(self):
		self.cursor_type = "row"
		self.zebra_stripes = True

		self.add_column("ID", key="id", width=6)
		self.add_column("Title", key="title", width=35)
		self.add_column("Artist", key="artist", width=15)
		self.add_column("Album", key="album", width=15)
		self.add_column("Genres", key="genres", width=15)
		self.add_column("Duration", key="duration", width=8)

	def clear_songs(self):
		self.clear(columns=False)
	
	def set_songs(self, songs):
		for song in songs:
			minutes = int((song["duration_ms"] / 1000) / 60)
			seconds = int((song["duration_ms"] / 1000) % 60)
			song_duration = "{}:{:02d}".format(minutes, seconds)
			self.add_row(song["id"], song["title"], song["artist"], song["album"], song["genres"], song_duration, key=song["id"])

# --- Playlist Button Widget --------------------------------------------------

class PlaylistButton(Static):

	def __init__(self, id: int, playlist_name: str, advanced_filter: str) -> None:
		super().__init__()
		self.playlist_name = playlist_name
		self.playlist_id = id
		self.advanced_filter = advanced_filter

	def compose(self) -> ComposeResult:
		yield Button("{}".format(self.playlist_name), id="btn-playlist-{}".format(self.playlist_id), classes="playlist-btn")
