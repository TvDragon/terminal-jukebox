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

		self.add_column("ID", width=6)
		self.add_column("Title", width=35)
		self.add_column("Artist", width=15)
		self.add_column("Album", width=15)
		self.add_column("Genres", width=15)
		self.add_column("Duration", width=8)

	async def clear_songs(self):
		await self.remove_children()
	
	def set_songs(self, songs):
		self.clear()

		for song in songs:
			minutes = int((song["duration_ms"] / 1000) / 60)
			seconds = int((song["duration_ms"] / 1000) % 60)
			song_duration = "{}:{:02d}".format(minutes, seconds)
			self.add_row(song["id"], song["title"], song["artist"], song["album"], song["genres"], song_duration, key=str(song["id"]))

# --- Playlist Button Widget --------------------------------------------------

class PlaylistButton(Static):

	def __init__(self, id: int, playlist_name: str) -> None:
		super().__init__()
		self.playlist_name = playlist_name
		self.playlist_id = id

	def compose(self) -> ComposeResult:
		yield Button("{}".format(self.playlist_name), id="btn-playlist-{}".format(self.playlist_id), classes="playlist-btn")