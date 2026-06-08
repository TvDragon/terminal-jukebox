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
		self.cursor_type = "row"
		self.zebra_stripes = True

		self.add_column("ID", width=4)
		self.add_column("Title", width=35)
		self.add_column("Artist", width=12)
		self.add_column("Album", width=12)
		self.add_column("Genres", width=12)
		self.add_column("Duration", width=8)
	
	def set_songs(self, songs):
		self.clear()

		for idx, song in enumerate(songs):
			minutes = int((song["duration_ms"] / 1000) / 60)
			seconds = int((song["duration_ms"] / 1000) % 60)
			song_duration = "{}:{:02d}".format(minutes, seconds)
			self.add_row(song["id"], song["title"], song["artist"], song["album"], song["genres"], song_duration, key=str(idx))

# --- Playlist Button Widget --------------------------------------------------

class PlaylistButton(Static):

	def __init__(self, id: int, playlist_name: str) -> None:
		super().__init__()
		self.playlist_name = playlist_name
		self.playlist_id = id

	def compose(self) -> ComposeResult:
		yield Button("{}".format(self.playlist_name), id="btn-playlist-{}".format(self.playlist_id), classes="playlist-btn")

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
		self.playlists = self.sql_db_connector.get_all_playlists()
		self.playlist_songs_active = []
		self.playlist_songs_view = []
		self.playlist_name = self.playlists[0]["playlist_name"] if len(self.playlists) > 0 else None
		self.playlist_id = self.playlists[0]["id"] if len(self.playlists) > 0 else 0
		self.current_tab = ""
		self.play_all_songs = True	# All songs library or specific playlist to play
		self.volume = 40
		self.btn_num_pressed = 0

		self.song_idx = -1
		self.is_playing = False
		self.current_position = 0
		self.duration = 0

		self.playback = Playback()
		self.playback.set_volume(self.volume / 100)
		self.progress_bar = make_progress_bar_timer(self.current_position, self.duration)

	def on_mount(self) -> None:
		music_table = self.query_one("#music-table", MusicTable)
		music_table.set_songs(self.all_songs)
		self.current_tab = self.query_one("#tabs", TabbedContent).active

		playlist_table = self.query_one("#songs-playlist-table", MusicTable)
		playlist_table.set_songs(self.playlist_songs_view)

		playlists_widget = self.query_one("#playlists", VerticalScroll)
		for playlist in self.playlists:
			playlists_widget.mount(PlaylistButton(playlist["id"], playlist["playlist_name"]))

		self.set_interval(1, self.update_progress)	# Update progress bar every second
		self.update_volume_bar()

		self.next_song()

	def load_songs(self) -> None:
		self.all_songs = self.sql_db_connector.get_all_songs()

	def load_playlist_view(self) -> None:
		if self.playlist_name != None:
			self.playlist_songs_view = self.sql_db_connector.get_songs_in_playlist(self.playlist_name)
	
	def update_progress(self) -> None:
		if self.is_playing:
			self.current_position += 1
			if self.current_position > self.duration:
				self.next_song()
				
			self.progress_bar = make_progress_bar_timer(self.current_position, self.duration)
			self.query_one("#progress-bar-song", Static).update(self.progress_bar)

	def load_song(self) -> None:
		self.current_position = 0
		curr_song = self.all_songs[self.song_idx] if self.play_all_songs else self.playlist_songs_active[self.song_idx]

		self.playback.load_file(curr_song["file_path"])
		self.duration = int(curr_song["duration_ms"] / 1000)
		
		self.query_one("#lbl-title", Label).update("[bold]{}[/bold]".format(curr_song["title"]))
		self.query_one("#lbl-artist", Label).update(curr_song["artist"])

		if self.is_playing:
			btn = self.query_one("#btn-play-pause", Button)
			btn.label = "\u23f8 Pause"
			self.playback.play()
		
		self.progress_bar = make_progress_bar_timer(self.current_position, self.duration)
		self.query_one("#progress-bar-song", Static).update(self.progress_bar)

	def previous_song(self) -> None:
		if len(self.all_songs) > 0:
			self.song_idx -= 1
			if self.song_idx < 0:
				if self.play_all_songs:
					self.song_idx = len(self.all_songs) - 1
				else:
					self.song_idx = len(self.playlist_songs_active) - 1
			self.load_song()

	def next_song(self) -> None:
		if len(self.all_songs) > 0:
			self.song_idx += 1
			if self.song_idx >= len(self.all_songs) and self.play_all_songs:
				self.song_idx = 0
			elif self.song_idx >= len(self.playlist_songs_active) and not self.play_all_songs:
				self.song_idx = 0
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
						with Horizontal(id="playlists-section"):
							with VerticalScroll(id="playlists"):
								yield Label("[bold]Playlists[/bold]", classes="title")
							with VerticalScroll(id="songs-playlist"):
								yield MusicTable(id="songs-playlist-table")

			# --- Bottom Section (Current song being played) ---
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
			self.load_playlist_view()
			table.set_songs(self.playlist_songs_view)
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
			for song in self.playlist_songs_view:
				if searched_music.lower() in normalise_text(song["title"]):
					results.append(song)
			table = self.query_one("#songs-playlist-table", MusicTable)
		table.set_songs(results)

	# --- Music Table Actions -------------------------------------------------

	@on(DataTable.RowSelected, "#music-table")
	def music_table_row_selected(self, event: DataTable.RowSelected) -> None:
		song_id = event.row_key.value

		self.song_idx = int(song_id)
		self.play_all_songs = True
		self.is_playing = True
		self.load_song()

	@on(DataTable.RowSelected, "#songs-playlist-table")
	def songs_playlist_table_row_selected(self, event: DataTable.RowSelected) -> None:
		song_id = event.row_key.value

		self.song_idx = int(song_id)
		self.play_all_songs = False
		self.is_playing = True
		self.playlist_songs_active = self.playlist_songs_view
		self.load_song()

	# --- Music Control Buttons -----------------------------------------------
	
	@on(Button.Pressed, ".playlist-btn")
	def pressed_btn_playlist(self, event: Button.Pressed) -> None:
		playlist_widget = event.button.parent

		self.query_one("#btn-playlist-{}".format(self.playlist_id), Button).remove_class("active-playlist-btn")
		event.button.add_class("active-playlist-btn")
		if self.playlist_name == playlist_widget.playlist_name:
			if self.btn_num_pressed == 1:
				btn = self.query_one("#btn-play-pause", Button)
				btn.label = "\u23f8 Pause"
				self.play_all_songs = False
				self.song_idx = 0
				self.is_playing = True
				self.playlist_songs_active = self.sql_db_connector.get_songs_in_playlist(self.playlist_name)
				self.load_song()
		else:
			self.playlist_name = playlist_widget.playlist_name
			self.playlist_id = playlist_widget.playlist_id
			self.load_playlist_view()

			playlist_table = self.query_one("#songs-playlist-table", MusicTable)
			playlist_table.set_songs(self.playlist_songs_view)
			self.btn_num_pressed = 0
		self.btn_num_pressed += 1

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
		self.btn_num_pressed = 0

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