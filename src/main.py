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
from textual.widgets._data_table import RowKey
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

from models.model import SongAction, SongMenuResult, SongPlaylists, SongInfo, PlaylistAction, PlaylistMenuResult
from services.database_handler import SQL_Connector
from services.library_service import LibaryService
from services.music_player import MusicPlayer
from widgets.widgets import MusicTable, PlaylistButton
from widgets.popups import ScanFoldersWidget, DeleteFilePopup, SongSubMenu, LoadingScreen, NewPlaylistPopup, PlaylistSubMenu
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
		self.playlist_id = self.playlists[0]["id"] if len(self.playlists) > 0 else -1	
		self.current_tab = ""
		self.play_all_songs = True	# All songs library or specific playlist to play
		self.btn_num_pressed = 0
		self.mouse_click = None

		self.progress_bar = make_progress_bar_timer(self.music_player.get_current_song_position(),
											  			self.music_player.get_song_duration())

	async def on_mount(self) -> None:
		music_table = self.query_one("#music-table", MusicTable)
		music_table.clear_songs()
		music_table.set_songs(self.all_songs)
		self.current_tab = self.query_one("#tabs", TabbedContent).active

		playlist_table = self.query_one("#songs-playlist-table", MusicTable)
		playlist_table.clear_songs()
		playlist_table.set_songs(self.playlist_songs_view)

		await self._update_playlists_view()

		self.set_interval(1, self._update_progress)	# Update progress bar every second
		self._update_volume_bar()

		self._next_song()

	async def _update_playlists_view(self) -> None:
		self.playlists = self.library_service.get_playlists()

		playlists_widget = self.query_one("#playlists", VerticalScroll)
		await playlists_widget.remove_children()

		for playlist in self.playlists:
			playlists_widget.mount(PlaylistButton(playlist["id"], playlist["playlist_name"]))

	def _update_music_table(self) -> None:
		music_table = self.query_one("#music-table", MusicTable)
		music_table.clear_songs()
		self.all_songs = self.library_service.get_all_songs()
		music_table.set_songs(self.all_songs)

	def _load_songs(self) -> None:
		self.all_songs = self.library_service.get_all_songs()

	def _load_playlist_view(self) -> None:
		if self.playlist_name != None:
			self.playlist_songs_view = self.library_service.get_playlist_songs(self.playlist_name)

	def _stop_and_reset(self) -> None:
		self.music_player.reset_position()
		self.music_player.stop_play()
		self.progress_bar = make_progress_bar_timer(self.music_player.get_current_song_position(),
											   self.music_player.get_song_duration())
		self.query_one("#progress-bar-song", Static).update(self.progress_bar)
	
	def _update_progress(self) -> None:
		if self.music_player.get_is_playing():
			self.music_player.update_position()
			if self.music_player.get_current_song_position() > self.music_player.get_song_duration():
				self._next_song()
				
			self.progress_bar = make_progress_bar_timer(self.music_player.get_current_song_position(),
											   self.music_player.get_song_duration())
			self.query_one("#progress-bar-song", Static).update(self.progress_bar)

	def _load_song(self, view: str = "") -> None:
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
							music_table.remove_row(RowKey(curr_song["id"]))
						elif not self.play_all_songs:
							if view == "playlist-view":
								if len(self.playlist_songs_view) > 0:
									for idx, song in enumerate(self.playlist_songs_view):
										if song["id"] == song_idx:
											self.playlist_songs_view.pop(idx)
											break
									playlist_table = self.query_one("#songs-playlist-table", MusicTable)
									playlist_table.clear_songs()
									playlist_table.set_songs(self.playlist_songs_view)
							elif len(self.playlist_songs_active) > 0:
									self._load_playlist_view()
									self.playlist_songs_active = self.playlist_songs_view
									playlist_table = self.query_one("#songs-playlist-table", MusicTable)
									playlist_table.clear_songs()
									playlist_table.set_songs(self.playlist_songs_view)

				self.push_screen(DeleteFilePopup("File does not exist: {}".format(curr_song["file_path"])), delete_song)
		else:
			self._stop_and_reset()

	def _previous_song(self) -> None:
		if self.play_all_songs and len(self.all_songs) > 0:
			idx = self.music_player.get_song_idx()
			for i, song in enumerate(self.all_songs):
				if song["id"] == idx:
					self.music_player.set_song_idx(self.all_songs[i-1]["id"])
			self._load_song()
		elif len(self.playlist_songs_active) > 0:
			idx = self.music_player.get_song_idx()
			for i, song in enumerate(self.playlist_songs_active):
				if song["id"] == idx:
					self.music_player.set_song_idx(self.playlist_songs_active[i-1]["id"])
			self._load_song()
			
	def _next_song(self) -> None:
		if self.play_all_songs and len(self.all_songs) > 0:
			idx = self.music_player.get_song_idx()
			for i, song in enumerate(self.all_songs):
				if song["id"] == idx:
					self.music_player.set_song_idx(self.all_songs[(i+1) % len(self.all_songs)]["id"])
			self._load_song()
		elif len(self.playlist_songs_active) > 0:
			idx = self.music_player.get_song_idx()
			for i, song in enumerate(self.playlist_songs_active):
				if song["id"] == idx:
					self.music_player.set_song_idx(self.playlist_songs_active[(i+1) % len(self.playlist_songs_active)]["id"])
			self._load_song()

	def _update_volume_bar(self):
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
			self._update_music_table()
		elif tab_id == "tab-playlists":
			table = self.query_one("#songs-playlist-table", MusicTable)
			self._load_playlist_view()
			table.clear_songs()
			table.set_songs(self.playlist_songs_view)
		self.current_tab = tab_id

	# --- Scan Music Folders Button -------------------------------------------

	@on(Button.Pressed, "#btn-scan")
	def pressed_scan_files(self) -> None:

		def scan_folders(new_music_folders: (list | None)) -> None:
			if new_music_folders:
				self._scan_selected_folders(new_music_folders)

		self.push_screen(ScanFoldersWidget(self.library_service.get_music_folders()), scan_folders)

	@work(thread=True)
	def _scan_selected_folders(self, new_music_folders) -> None:
		self.call_from_thread(self.push_screen, LoadingScreen())

		for folder in new_music_folders:
			if folder["checked"] == True:
				if not self.library_service.check_folder_exists(folder["folder_path"]):
					self.library_service.add_music_folder(folder["folder_path"])
				self.library_service.add_songs_from_folder(folder["folder_path"])
			elif self.library_service.check_folder_exists(folder["folder_path"]) and folder["checked"] == False:
				self.library_service.remove_music_folder(folder["folder_path"])
		
		self.call_from_thread(self._scan_finished)

	def _scan_finished(self) -> None:
		self._update_music_table()
		self.pop_screen()

	# --- Create New Playlist Button -------------------------------------------

	@on(Button.Pressed, "#btn-create-playlist")
	def pressed_create_playlist(self) -> None:

		async def create_new_playlist(result : (dict | None)) -> None:
			if result:
				self.library_service.add_playlist(result["playlist_name"], result["is_auto_playlist"])
				await self._update_playlists_view()

		self.push_screen(NewPlaylistPopup(), create_new_playlist)

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
		table.clear_songs()
		table.set_songs(results)

	# --- Music Table Actions -------------------------------------------------

	@on(DataTable.RowSelected, "#music-table")
	def music_table_row_selected(self, event: DataTable.RowSelected) -> None:
		if event.row_key != None:
			song_id = int(event.row_key.value)
			if self.mouse_click == 1:
				self.play_all_songs = True
				self._play_selected_song(song_id)
			self.check_right_click_music_table(song_id)

	@on(DataTable.RowSelected, "#songs-playlist-table")
	def songs_playlist_table_row_selected(self, event: DataTable.RowSelected) -> None:
		if event.row_key != None:
			song_id = int(event.row_key.value)
			if self.mouse_click == 1:
				self.play_all_songs = False
				self.playlist_songs_active = self.playlist_songs_view
				self._play_selected_song(song_id, "playlist-view")
			self.check_right_click_songs_playlist_table(song_id)

	@on(DataTable.RowHighlighted, "#music-table")
	def music_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
		if event.row_key != None:
			song_id = int(event.row_key.value)
			self.check_right_click_music_table(song_id)

	@on(DataTable.RowHighlighted, "#songs-playlist-table")
	def songs_playlist_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
		if event.row_key != None:
			song_id = int(event.row_key.value)
			self.check_right_click_songs_playlist_table(song_id)

	def check_right_click_music_table(self, song_id: int) -> None:
		idx = 0
		if self.mouse_click == 3:
			curr_song = None
			for i, song in enumerate(self.all_songs):
				if song["id"] == song_id:
					curr_song = song
					idx = i
					break
			playlists = self.library_service.get_playlists()
			in_playlists = self.library_service.get_playlists_for_song(song_id, playlists)	# E.g. [{"playlist_id": 2, "in_playlist": True}]

			song_playlists = []
			for playlist in playlists:
				song_playlists.append(SongPlaylists(playlist["id"],
													playlist["playlist_name"],
													song_id,
													in_playlists[playlist["id"]],
													playlist["is_auto_playlist"]))
			
			async def sub_menu_task(result: SongMenuResult | None):
				if result:
					if result.action == SongAction.PLAY:
						self.play_all_songs = True
						self._play_selected_song(song_id)
					if result.action == SongAction.EDIT:
						song = result.payload
						self.library_service.edit_song(song.id, song.title, song.artist, song.album, song.genres, song.file_path)
						music_table = self.query_one("#music-table", MusicTable)
						self.all_songs[idx] = self.library_service.get_song(song.id)
						music_table.update_cell(RowKey(song.id), music_table.columns["title"].key, song.title)
						music_table.update_cell(RowKey(song.id), music_table.columns["artist"].key, song.artist)
						music_table.update_cell(RowKey(song.id), music_table.columns["album"].key, song.album)
						music_table.update_cell(RowKey(song.id), music_table.columns["genres"].key, song.genres)
					elif result.action == SongAction.UPDATE_TO_PLAYLIST:
						options = result.payload
						for playlist in playlists:
							if not playlist["is_auto_playlist"]:
								playlist_id = playlist["id"]
								selected = options[playlist_id]
								if not in_playlists[playlist_id] and selected == True:
									self.library_service.add_song_to_playlist(song_id, playlist_id)
								elif in_playlists[playlist_id] and selected == False:
									await self.remove_song_from_playlist(song_id, playlist_id)
					elif result.action == SongAction.DELETE:
						await self.delete_selected_song(curr_song, idx)

			self.push_screen(SongSubMenu(SongInfo(curr_song["id"], curr_song["title"],
										 curr_song["artist"], curr_song["album"],
										 curr_song["genres"], curr_song["file_path"]),
										 song_playlists, True), sub_menu_task)

	def check_right_click_songs_playlist_table(self, song_id: int) -> None:
		if self.mouse_click == 3:
			curr_song = None
			for song in self.playlist_songs_view:
				if song["id"] == song_id:
					curr_song = song
					break
			playlists = self.library_service.get_playlists()
			in_playlists = self.library_service.get_playlists_for_song(song_id, playlists)	# E.g. [{"playlist_id": 2, "in_playlist": True}]

			song_playlists = []
			for playlist in playlists:
				song_playlists.append(SongPlaylists(playlist["id"],
													playlist["playlist_name"],
													song_id,
													in_playlists[playlist["id"]],
													playlist["is_auto_playlist"]))
			
			async def sub_menu_task(result: SongMenuResult | None):
				if result:
					if result.action == SongAction.PLAY:
						self.play_all_songs = False
						self.playlist_songs_active = self.playlist_songs_view
						self._play_selected_song(song_id, "playlist-view")
					if result.action == SongAction.EDIT:
						song = result.payload
						self.library_service.edit_song(song.id, song.title, song.artist, song.album, song.genres)
						playlist_table = self.query_one("#songs-playlist-table", MusicTable)
						self.playlist_songs_view = self.library_service.get_playlist_songs(self.playlist_name)
						playlist_table.update_cell(RowKey(song.id), playlist_table.columns["title"].key, song.title)
						playlist_table.update_cell(RowKey(song.id), playlist_table.columns["artist"].key, song.artist)
						playlist_table.update_cell(RowKey(song.id), playlist_table.columns["album"].key, song.album)
						playlist_table.update_cell(RowKey(song.id), playlist_table.columns["genres"].key, song.genres)
					elif result.action == SongAction.UPDATE_TO_PLAYLIST:
						options = result.payload
						for playlist in playlists:
							if not playlist["is_auto_playlist"]:
								playlist_id = playlist["id"]
								selected = options[playlist_id]
								if not in_playlists[playlist_id] and selected == True:
									self.library_service.add_song_to_playlist(song_id, playlist_id)
								elif in_playlists[playlist_id] and selected == False:
									await self.remove_song_from_playlist(song_id, playlist_id)
					elif result.action == SongAction.REMOVE:
						await self.remove_song_from_playlist(song_id, self.playlist_id)

			self.push_screen(SongSubMenu(SongInfo(curr_song["id"], curr_song["title"],
										 curr_song["artist"], curr_song["album"],
										 curr_song["genres"], curr_song["file_path"]), song_playlists, False), sub_menu_task)

	def _play_selected_song(self, song_id: int, view: str ="") -> None:
		self.music_player.set_song_idx(song_id)
		self.music_player.set_play()
		self._load_song(view)

	async def delete_selected_song(self, curr_song, idx: int) -> None:
		self.library_service.delete_song(curr_song["id"])
		if len(self.all_songs) > 0:
			self.all_songs.pop(idx)
			music_table = self.query_one("#music-table", MusicTable)
			music_table.remove_row(RowKey(curr_song["id"]))

	async def remove_song_from_playlist(self, song_id: int, playlist_id: int):
		self.library_service.remove_song_from_playlist(song_id, playlist_id)

		if self.playlist_id == playlist_id:
			if len(self.playlist_songs_active) > 0:
				for i, song in enumerate(self.playlist_songs_active):
					if song["id"] == song_id:
						self.playlist_songs_active.pop(i)
						break

			if len(self.playlist_songs_view) > 0:
				for i, song in enumerate(self.playlist_songs_view):
					if song["id"] == song_id:
						self.playlist_songs_view.pop(i)
						break
				playlist_table = self.query_one("#songs-playlist-table", MusicTable)
				playlist_table.clear_songs()
				playlist_table.set_songs(self.playlist_songs_view)
		
	# --- Music Control Buttons -----------------------------------------------
	
	@on(Button.Pressed, ".playlist-btn")
	async def pressed_btn_playlist(self, event: Button.Pressed) -> None:
		playlist_widget = event.button.parent
		if self.mouse_click == 1:

			if self.playlist_id != -1:
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
					self._load_song("playlist-view")
			else:
				self.playlist_name = playlist_widget.playlist_name
				self.playlist_id = playlist_widget.playlist_id
				self._load_playlist_view()

				playlist_table = self.query_one("#songs-playlist-table", MusicTable)
				playlist_table.clear_songs()
				playlist_table.set_songs(self.playlist_songs_view)
				self.btn_num_pressed = 0
			self.btn_num_pressed += 1
		elif self.mouse_click == 3:
			playlist_id = playlist_widget.playlist_id
			playlist_name = playlist_widget.playlist_name

			async def sub_menu_task(result: PlaylistMenuResult | None):
				if result:
					if result.action == PlaylistAction.EDIT:
						new_playlist_name = result.payload["playlist_name"]
						self.library_service.update_playlist(playlist_id, new_playlist_name)
						await self._update_playlists_view()
					elif result.action == PlaylistAction.DELETE:
						self.library_service.delete_playlist(playlist_id)	# CASCADE delete rows in SONGS_PLAYLISTS that have this playlist_id
						await self._update_playlists_view()
						if playlist_id == self.playlist_id:
							self.playlist_id = -1

			self.push_screen(PlaylistSubMenu(playlist_name), sub_menu_task)	
			

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
			self._previous_song()

	@on(Button.Pressed, "#btn-next")
	def pressed_next_song(self) -> None:
		if self.mouse_click == 1:
			self._next_song()

	# --- Mouse Click ---------------------------------------------------------
	
	def on_mouse_down(self, event: events.MouseDown) -> None:
		self.mouse_click = event.button

	# --- Action Key Bindings -------------------------------------------------

	def action_volume_up(self) -> None:
		self.music_player.increase_volume(5)
		self._update_volume_bar()

	def action_volume_down(self) -> None:
		self.music_player.decrease_volume(5)
		self._update_volume_bar()

# --- Entry Point -------------------------------------------------------------

if __name__ == "__main__":

	TerminalJukeBox.SUB_TITLE = "v1.0"
	app = TerminalJukeBox()
	app.run()
