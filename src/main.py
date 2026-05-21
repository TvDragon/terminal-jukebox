from time import monotonic

from textual import events, on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import (
	Container,
	Horizontal,
	HorizontalGroup,
	Vertical,
	VerticalGroup,
	VerticalScroll
)
from textual.screen import ModalScreen
from textual.suggester import Suggester
from textual.widgets import (
	Button,
	DataTable,
	Footer,
	Header,
	Input,
	Label,
	RadioButton,
	RadioSet,
	RichLog,
	SelectionList,
	Static,
	TabbedContent,
	TabPane,
)
from textual.widgets.selection_list import Selection

from database_handler import SQL_Connector

# --- Music Table View --------------------------------------------------------

# --- Main Application --------------------------------------------------------

class MusicTable(DataTable):

	def on_mount(self):
		self.add_column("ID", width=4)
		self.add_column("Title", width=35)
		self.add_column("Artist", width=12)
		self.add_column("Album", width=12)
		self.add_column("Genres", width=12)
		self.add_column("Duration", width=8)
	
	def set_songs(self, songs):
		self.clear()

		for song in songs:
			minutes = int((song["duration_ms"] / 1000) / 60)
			seconds = int((song["duration_ms"] / 1000) % 60)
			song_duration = "{}:{:02d}".format(minutes, seconds)
			self.add_row(song["id"], song["title"], song["artist"], song["album"], song["genres"], song_duration)

class TerminalJukeBox(App):
	"""Terminal Jukebox - Music Player"""
	
	TITLE = "Terminal Jukebox"
	SUB_TITLE = "v1.0"
	
	CSS_PATH = "terminal-jukebox.tcss"
	BINDINGS = [
		Binding("ctrl+q", "quit", "Quit"),
	]

	def __init__(self):
		super().__init__()
		self.home_image_path = "assets/home.png"
		self.sql_db_connector = SQL_Connector()
		self.all_songs = self.sql_db_connector.get_all_songs()
		self.playlist_name = "Vinahouse"

	def on_mount(self):
		table = self.query_one("#music-table", MusicTable)
		table.set_songs(self.all_songs)

	def load_songs(self):
		self.all_songs = self.sql_db_connector.get_all_songs()

	def load_playlist(self) -> list:
		if self.playlist_name != None:
			return self.sql_db_connector.get_songs_in_playlist(self.playlist_name)
		return []

	def compose(self) -> ComposeResult:
		yield Header()

		with Container(id="root"):
			# --- Top Bar (Home and search bar) ---
			with Container(id="top-box", classes="box"):
				with Horizontal(id="top-bar", classes="main-border"):
					yield Button("Scan", id="btn-scan")
					yield Button("Home", id="btn-home")
					yield Input(
						placeholder="Search for music...",
						id="music-search-input"
					)
					yield Button("Search", id="btn-search")

			with Container(id="main-box", classes="box main-border"):
				# --- Middle Section (Playlists and songs) ---
				with TabbedContent("Music", "Playlists", id="tabs"):
					# --- All Songs Tab ---
					with TabPane("Music", id="tab-music"):
						yield Label("[bold]Songs[/bold]")
						with VerticalScroll(id="music-group"):
							yield MusicTable(id="music-table")

					# --- All Playlists Tab ---
					with TabPane("Playlists", id="tab-playlists"):
						yield Label("[bold]Playlists[/bold]")
						with VerticalScroll(id="songs-playlist"):
							yield MusicTable(id="songs-playlist-table")

			# --- Bottom Section (Current song being played) ---
		yield Footer()

	# Event handler for TabbedContent switching on Music TabbedContent
	@on(TabbedContent.TabActivated, "#tabs")
	def musics_tab_pressed(self, event: TabbedContent.TabActivated) -> None:
		tab_id = event.pane.id

		if tab_id == "tab-music":
			table = self.query_one("#music-table", MusicTable)
			self.load_songs()
			table.set_songs(self.all_songs)
		elif tab_id == "tab-playlists":

			table = self.query_one("#songs-playlist-table", MusicTable)
			songs = self.load_playlist()
			table.set_songs(songs)

# --- Entry Point -------------------------------------------------------------

if __name__ == "__main__":

	TerminalJukeBox.SUB_TITLE = "v1.0"
	app = TerminalJukeBox()
	app.run()