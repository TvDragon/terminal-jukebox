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

from services.database_handler import SQL_Connector
from services.library_service import LibaryService
from services.music_player import MusicPlayer
from widgets.widgets import MusicTable, PlaylistButton
from widgets.popups import ScanFoldersWidget, DeleteFilePopup
from utils import normalise_text

import os

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
		self.library_service = LibaryService()
		self.music_player = MusicPlayer()
		self.all_songs = self.library_service.get_all_songs()
		self.playlists = self.library_service.get_playlists()
		self.playlist_songs_active = []
		self.playlist_songs_view = []
		self.playlist_name = self.playlists[0]["playlist_name"] if len(self.playlists) > 0 else None
		self.playlist_id = self.playlists[0]["id"] if len(self.playlists) > 0 else 0
		self.current_tab = ""
		self.play_all_songs = True	# All songs library or specific playlist to play
		self.btn_num_pressed = 0
		self.mouse_click = None

		self.progress_bar = make_progress_bar_timer(self.music_player.get_current_song_position(),
											  			self.music_player.get_song_duration())

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
		self.all_songs = self.library_service.get_all_songs()

	def load_playlist_view(self) -> None:
		if self.playlist_name != None:
			self.playlist_songs_view = self.library_service.get_playlist_songs(self.playlist_name)

	def stop_and_reset(self) -> None:
		self.music_player.reset_position()
		self.music_player.stop_play()
		self.progress_bar = make_progress_bar_timer(self.music_player.get_current_song_position(),
											   self.music_player.get_song_duration())
		self.query_one("#progress-bar-song", Static).update(self.progress_bar)
	
	def update_progress(self) -> None:
		if self.music_player.get_is_playing():
			self.music_player.update_position()
			if self.music_player.get_current_song_position() > self.music_player.get_song_duration():
				self.next_song()
				
			self.progress_bar = make_progress_bar_timer(self.music_player.get_current_song_position(),
											   self.music_player.get_song_duration())
			self.query_one("#progress-bar-song", Static).update(self.progress_bar)

	def load_song(self, view: str = "") -> None:
		song_idx = self.music_player.get_song_idx()
		curr_song = None
		if self.play_all_songs:
			if len(self.all_songs) > 0:
				for song in self.all_songs:
					if song["id"] == song_idx:
						curr_song = song
						break
		elif len(self.playlist_songs_active) > 0:
			for song in self.playlist_songs_active:
				if song["id"] == song_idx:
					curr_song = song
					break

		if curr_song != None:
			if os.path.isfile(curr_song["file_path"]):
				self.music_player.load_song(curr_song)
				self.query_one("#lbl-title", Label).update("[bold]{}[/bold]".format(curr_song["title"]))
				self.query_one("#lbl-artist", Label).update(curr_song["artist"])

				if self.music_player.get_is_playing():
					btn = self.query_one("#btn-play-pause", Button)
					btn.label = "\u23f8 Pause"
					self.music_player.play()
				
				self.progress_bar = make_progress_bar_timer(self.music_player.get_current_song_position(),
													self.music_player.get_song_duration())
				self.query_one("#progress-bar-song", Static).update(self.progress_bar)
			else:			
				async def delete_song(confirmed: bool) -> None:
					if confirmed:
						self.library_service.delete_song(curr_song["id"])
						if self.play_all_songs and len(self.all_songs) > 0:
							for idx, song in enumerate(self.all_songs):
								if song["id"] == song_idx:
									self.all_songs.pop(idx)
									break
							music_table = self.query_one("#music-table", MusicTable)
							await music_table.clear_songs()
							self.all_songs = self.library_service.get_all_songs()
							music_table.set_songs(self.all_songs)
						elif not self.play_all_songs:
							if view == "playlist-view":
								if len(self.playlist_songs_view) > 0:
									for idx, song in enumerate(self.playlist_songs_view):
										if song["id"] == song_idx:
											self.playlist_songs_view.pop(idx)
											break
									playlist_table = self.query_one("#songs-playlist-table", MusicTable)
									playlist_table.set_songs(self.playlist_songs_view)
							elif len(self.playlist_songs_active) > 0:
									self.load_playlist_view()
									self.playlist_songs_active = self.playlist_songs_view
									playlist_table = self.query_one("#songs-playlist-table", MusicTable)
									playlist_table.set_songs(self.playlist_songs_view)

				self.push_screen(DeleteFilePopup("File does not exist: {}".format(curr_song["file_path"])), delete_song)
		else:
			self.stop_and_reset()

	def previous_song(self) -> None:
		if self.play_all_songs and len(self.all_songs) > 0:
			idx = self.music_player.get_song_idx()
			for i, song in enumerate(self.all_songs):
				if song["id"] == idx:
					self.music_player.set_song_idx(self.all_songs[i-1]["id"])
			self.load_song()
		elif len(self.playlist_songs_active) > 0:
			idx = self.music_player.get_song_idx()
			for i, song in enumerate(self.playlist_songs_active):
				if song["id"] == idx:
					self.music_player.set_song_idx(self.playlist_songs_active[i-1]["id"])
			self.load_song()
			
	def next_song(self) -> None:
		if self.play_all_songs and len(self.all_songs) > 0:
			idx = self.music_player.get_song_idx()
			for i, song in enumerate(self.all_songs):
				if song["id"] == idx:
					self.music_player.set_song_idx(self.all_songs[(i+1) % len(self.all_songs)]["id"])
			self.load_song()
		elif len(self.playlist_songs_active) > 0:
			idx = self.music_player.get_song_idx()
			for i, song in enumerate(self.playlist_songs_active):
				if song["id"] == idx:
					self.music_player.set_song_idx(self.playlist_songs_active[(i+1) % len(self.playlist_songs_active)]["id"])
			self.load_song()

	def update_volume_bar(self):
		self.query_one("#volume-bar", Static).update(render_volume_bar(self.music_player.get_volume()))

	def compose(self) -> ComposeResult:
		yield Header()

		with Container(id="root"):
			# --- Top Bar (Home and search bar) ---
			with Container(id="top-box"):
				with Horizontal(id="top-bar", classes="main-border"):
					yield Button("Scan", id="btn-scan")
					yield Button("Create Playlist", id="btn-create-playlist")
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

	# --- Scan Music Folders Button -------------------------------------------

	@on(Button.Pressed, "#btn-scan")
	def pressed_scan_files(self) -> None:

		async def scan_folders(new_music_folders: (list | None)) -> None:
			if new_music_folders:
				for folder in new_music_folders:
					if folder["checked"] == True:
						if not self.library_service.check_folder_exists(folder["folder_path"]):
							self.library_service.add_music_folder(folder["folder_path"])
						self.library_service.add_songs_from_folder(folder["folder_path"])
					elif self.library_service.check_folder_exists(folder["folder_path"]) and folder["checked"] == False:
						self.library_service.remove_music_folder(folder["folder_path"])
				
				music_table = self.query_one("#music-table", MusicTable)
				await music_table.clear_songs()
				self.all_songs = self.library_service.get_all_songs()
				music_table.set_songs(self.all_songs)

		self.push_screen(ScanFoldersWidget(self.library_service.get_music_folders()), scan_folders)

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
		if self.mouse_click == 1:
			song_id = event.row_key.value
			self.music_player.set_song_idx(int(song_id))

			self.play_all_songs = True
			self.music_player.set_play()
			self.load_song()

	@on(DataTable.RowSelected, "#songs-playlist-table")
	def songs_playlist_table_row_selected(self, event: DataTable.RowSelected) -> None:
		if self.mouse_click == 1:
			song_id = event.row_key.value
			self.music_player.set_song_idx(int(song_id))

			self.play_all_songs = False
			self.music_player.set_play()
			self.playlist_songs_active = self.playlist_songs_view
			self.load_song("playlist-view")

	# --- Music Control Buttons -----------------------------------------------
	
	@on(Button.Pressed, ".playlist-btn")
	def pressed_btn_playlist(self, event: Button.Pressed) -> None:
		if self.mouse_click == 1:
			playlist_widget = event.button.parent

			self.query_one("#btn-playlist-{}".format(self.playlist_id), Button).remove_class("active-playlist-btn")
			event.button.add_class("active-playlist-btn")
			if self.playlist_name == playlist_widget.playlist_name:
				if self.btn_num_pressed == 1 and len(self.playlist_songs_view) > 0:
					btn = self.query_one("#btn-play-pause", Button)
					btn.label = "\u23f8 Pause"
					self.play_all_songs = False
					self.playlist_songs_active = self.playlist_songs_view
					self.music_player.set_song_idx(self.playlist_songs_active[0]["id"])
					self.music_player.set_play()
					self.load_song("playlist-view")
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
		if self.mouse_click == 1:
			btn = self.query_one("#btn-play-pause", Button)
			if self.music_player.get_is_playing():
				self.music_player.pause()
				btn.label = "\u25B6 Play"
			else:
				self.music_player.play()
				btn.label = "\u23f8 Pause"
			
			self.btn_num_pressed = 0

	@on(Button.Pressed, "#btn-prev")
	def pressed_prev_song(self) -> None:
		if self.mouse_click == 1:
			self.previous_song()

	@on(Button.Pressed, "#btn-next")
	def pressed_next_song(self) -> None:
		if self.mouse_click == 1:
			self.next_song()

	# --- Mouse Click ---------------------------------------------------------
	
	def on_mouse_down(self, event: events.MouseDown) -> None:
		self.mouse_click = event.button

	# --- Action Key Bindings -------------------------------------------------

	def action_volume_up(self) -> None:
		self.music_player.increase_volume(5)
		self.update_volume_bar()

	def action_volume_down(self) -> None:
		self.music_player.decrease_volume(5)
		self.update_volume_bar()

# --- Entry Point -------------------------------------------------------------

if __name__ == "__main__":

	TerminalJukeBox.SUB_TITLE = "v1.0"
	app = TerminalJukeBox()
	app.run()