from textual.app import ComposeResult
from textual.widgets import (
	Button,
	Static,
)

# --- Playlist Button Widget --------------------------------------------------

class PlaylistButton(Static):

	def __init__(self, id: int, playlist_name: str, advanced_filter: str) -> None:
		super().__init__()
		self.playlist_name = playlist_name
		self.playlist_id = id
		self.advanced_filter = advanced_filter

	def compose(self) -> ComposeResult:
		yield Button("{}".format(self.playlist_name), id="btn-playlist-{}".format(self.playlist_id), classes="playlist-btn")