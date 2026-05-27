from time import monotonic

from just_playback import Playback

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
from textual_slider import Slider
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

import unicodedata

from database_handler import SQL_Connector

def normalise_text(text: str) -> str:
	# NFD = Normalization Form Decomposed
	# Mn = Mark, Nonspacing
	normalised_text = unicodedata.normalize("NFD", text)

	final_text = ""
	for character in normalised_text:
		category = unicodedata.category(character)
		if category != "Mn":
			final_text += character

	return final_text.lower()

def make_bar(current: int, max: int, width: int) -> str:
	if max != 0:
		ratio = current / max
		filled = int(ratio * width)
		empty = width - filled
		return f"[{'█' * filled}{'-' * empty}]"

	return f"[{'-' * width}]"

def make_progress_bar_timer(current: int, duration: int, width: int=50) -> str:
	bar = make_bar(current, duration, width)
	progress_bar = "{}:{:02d} {} {}:{:02d}".format(int(current / 60),
													int(current % 60),
													bar,
													int(duration / 60),
													int(duration % 60))
	return progress_bar

def render_volume_bar(volume: int) -> str:
	total = 20

	filled = int((volume / 100) * total)
	empty = total - filled

	return (
			"[bold]🔊[/bold]"
			f"[green]{'─' * (filled - 1)}[green]"
			"[bold green]\u25a0[/bold green]"
			f"[grey]{'─' * empty}[grey]"
			f" {volume}%"
		)

# --- Music Table View --------------------------------------------------------

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


# --- Main Application --------------------------------------------------------

class TerminalJukeBox(App):
	"""Terminal Jukebox - Music Player"""
	
	TITLE = "Terminal Jukebox"
	SUB_TITLE = "v1.0"
	
	CSS_PATH = "terminal-jukebox.tcss"
	BINDINGS = [
		Binding("ctrl+q", "quit", "Quit"),
		Binding("ctrl+down", "volume_down", "Vol Down"),
		Binding("ctrl+up", "volume_up", "Vol Up"),
	]

	def __init__(self):
		super().__init__()
		self.sql_db_connector = SQL_Connector()
		self.all_songs = self.sql_db_connector.get_all_songs()
		self.playlist_songs = []
		self.playlist_name = None
		self.current_tab = ""
		self.play_all_songs = True	# All songs library or specific playlist to play
		self.volume = 40

		self.song_idx_playing = -1
		self.is_playing = False
		self.current_position = 0
		self.duration = 0

		self.playback = Playback()
		self.playback.set_volume(self.volume / 100)
		self.progress_bar = make_progress_bar_timer(self.current_position, self.duration)

	def on_mount(self) -> None:
		table = self.query_one("#music-table", MusicTable)
		table.set_songs(self.all_songs)
		self.current_tab = self.query_one("#tabs", TabbedContent).active

		self.set_interval(1, self.update_progress)	# Update progress bar every second
		self.update_volume_bar()

		self.next_song()

	def load_songs(self) -> None:
		self.all_songs = self.sql_db_connector.get_all_songs()

	def load_playlist(self) -> list:
		if self.playlist_name != None:
			self.playlist_songs = self.sql_db_connector.get_songs_in_playlist(self.playlist_name)
		return self.playlist_songs
	
	def update_progress(self) -> None:
		if self.is_playing:
			self.current_position += 1
			if self.current_position > self.duration:
				self.next_song()
				
			self.progress_bar = make_progress_bar_timer(self.current_position, self.duration)
			self.query_one("#progress-bar-song", Static).update(self.progress_bar)

	def load_song(self) -> None:
		self.playback.load_file(self.all_songs[self.song_idx_playing]["file_path"])
		self.duration = int(self.all_songs[self.song_idx_playing]["duration_ms"] / 1000)
		if self.is_playing:
			self.playback.play()
		
		self.query_one("#lbl-title", Label).update("[bold]{}[/bold]".format(self.all_songs[self.song_idx_playing]["title"]))
		self.query_one("#lbl-artist", Label).update(self.all_songs[self.song_idx_playing]["artist"])
		
		self.progress_bar = make_progress_bar_timer(self.current_position, self.duration)
		self.query_one("#progress-bar-song", Static).update(self.progress_bar)

	def previous_song(self) -> None:
		if len(self.all_songs) > 0:
			self.current_position = 0
			self.song_idx_playing -= 1
			# TODO: Get length of all songs or playlist. Cannot go to end of song library or playlist
			self.load_song()

	def next_song(self) -> None:
		if len(self.all_songs) > 0:
			self.current_position = 0
			self.song_idx_playing += 1
			# TODO: Get length of all songs or playlist. Stop playing if finished.
			self.load_song()

	def update_volume_bar(self):
		self.query_one("#volume-bar", Static).update(render_volume_bar(self.volume))

	def compose(self) -> ComposeResult:
		yield Header()

		with Container(id="root"):
			# --- Top Bar (Home and search bar) ---
			with Container(id="top-box"):
				with Horizontal(id="top-bar", classes="main-border"):
					yield Button("Scan", id="btn-scan")
					yield Input(
						placeholder="Search for music...",
						id="music-search-input"
					)

			with Container(id="main-box", classes="main-border"):
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

			with Container(id="bottom-box"):
				with Horizontal(id="bottom-bar"):
					with Vertical(id="song-info"):
						yield Label("[bold]Title[/bold]", id="lbl-title")
						yield Label("Artist", id="lbl-artist")
					with Vertical(id="music-player"):
						with Horizontal(id="music-controls", classes="music-btns"):
							yield Button("\u23ee Prev", id="btn-prev")
							yield Button("\u25b6 Play", id="btn-play-pause")
							yield Button("\u23ed Next", id="btn-next")
						yield Static(self.progress_bar, id="progress-bar-song")
					with Horizontal(id="volume-control"):
						yield Static("", id="volume-bar")

			# --- Bottom Section (Current song being played) ---
		yield Footer()

	# --- Tabbed Content handler ----------------------------------------------
	
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
		self.current_tab = tab_id

	# --- Search Bar ----------------------------------------------------------
	
	@on(Input.Changed, "#music-search-input")
	def update_search_music(self, event: Input.Changed) -> None:
		searched_music = normalise_text(event.value)

		results = []
		table = None
		if self.current_tab == "tab-music":
			for song in self.all_songs:
				if searched_music in normalise_text(song["title"]):
					results.append(song)
			table = self.query_one("#music-table", MusicTable)
		elif self.current_tab == "tab-playlists":
			for song in self.playlist_songs:
				if searched_music.lower() in normalise_text(song["title"]):
					results.append(song)
			table = self.query_one("#songs-playlist-table", MusicTable)
		table.set_songs(results)

	# --- Music Control Buttons -----------------------------------------------

	@on(Button.Pressed, "#btn-play-pause")
	def pressed_play_pause_song(self) -> None:
		self.is_playing = not self.is_playing

		btn = self.query_one("#btn-play-pause", Button)
		if self.is_playing:
			btn.label = "\u23f8 Pause"
			self.playback.play()
			self.playback.seek(self.current_position)
		else:
			btn.label = "\u25B6 Play"
			self.playback.pause()

	@on(Button.Pressed, "#btn-prev")
	def pressed_prev_song(self) -> None:
		self.previous_song()

	@on(Button.Pressed, "#btn-next")
	def pressed_next_song(self) -> None:
		self.next_song()

	# --- Action Key Bindings -----------------------------------------------

	def action_volume_up(self) -> None:
		self.volume = min(100, self.volume + 5)

		self.playback.set_volume(self.volume / 100)

		self.update_volume_bar()

	def action_volume_down(self) -> None:
		self.volume = max(0, self.volume - 5)

		self.playback.set_volume(self.volume / 100)

		self.update_volume_bar()

# --- Entry Point -------------------------------------------------------------

if __name__ == "__main__":

	TerminalJukeBox.SUB_TITLE = "v1.0"
	app = TerminalJukeBox()
	app.run()