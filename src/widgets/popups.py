from pathlib import Path
from textual import on
from textual.app import ComposeResult
from textual.containers import (
	Container,
	Horizontal,
	Vertical,
	VerticalScroll
)
from textual.events import Click
from textual.widgets.option_list import Option
from textual.screen import ModalScreen
from textual.widgets import (
	Button,
	Checkbox,
	DirectoryTree,
	Input,
	Label,
	LoadingIndicator,
	OptionList,
	SelectionList,
	Static,
)
from textual.widgets.selection_list import Selection

from models.model import SongAction, SongMenuResult, SongInfo, PlaylistAction, PlaylistMenuResult, FoldersScannedInfo
from utils import calculate_hash

import os

# --- Loading Screen Popup ----------------------------------------------------

class LoadingScreen(ModalScreen):
	"""A modal confirmation dialog."""

	DEFAULT_CSS = """
	LoadingScreen {
		align: center middle;
	}
	"""

	def __init__(self) -> None:
		super().__init__()

	def compose(self) -> ComposeResult:
		with Vertical():
			yield Label("Loading Data")
			yield LoadingIndicator()

# --- Confirm Dialog ----------------------------------------------------------

class ConfirmDialog(ModalScreen[bool]):
	"""A modal confirmation dialog."""

	DEFAULT_CSS = """
	ConfirmDialog {
		align: center middle;
	}
	"""

	def __init__(self, message: str) -> None:
		super().__init__()
		self.message = message

	def compose(self) -> ComposeResult:
		with Container(id="confirm-dialog"):
			yield Static(self.message)
			with Horizontal(classes="dialog-buttons"):
				yield Button("Confirm", variant="success", id="confirm-yes")
				yield Button("Cancel", variant="error", id="confirm-no")

	@on(Button.Pressed, "#confirm-yes")
	def on_confirm(self) -> None:
		self.dismiss(True)

	@on(Button.Pressed, "#confirm-no")
	def on_cancel(self) -> None:
		self.dismiss(False)

# --- Music Folders Dialog ----------------------------------------------------

class FolderDialog(ModalScreen[str | None]):

	DEFAULT_CSS = """
	FolderDialog {
		align: center middle;
	}
	"""

	def compose(self) -> ComposeResult:
		with Container(id="folder-dialog"):
			yield Static("Folders...")
			yield DirectoryTree(Path("/"), id="folder-tree")
			with Horizontal(classes="dialog-buttons"):
				yield Button("Add", variant="success", id="btn-folder-yes")
				yield Button("Cancel", variant="error", id="btn-folder-cancel")

	@on(Button.Pressed, "#btn-folder-yes")
	def on_confirm(self) -> (str | None):
		tree = self.query_one("#folder-tree", DirectoryTree)
		node = tree.cursor_node
		if node is not None:
			self.dismiss(node.data.path)
		else:	
			self.dismiss(None)			

	@on(Button.Pressed, "#btn-folder-cancel")
	def on_cancel(self) -> None:
		self.dismiss(None)	

# --- Scan Folders Widget -----------------------------------------------------

class ScanFoldersWidget(ModalScreen[list | None]):

	DEFAULT_CSS = """
	ScanFoldersWidget {
		align: center middle;
	}
	"""

	def __init__(self, music_folders: list[FoldersScannedInfo]) -> None:
		super().__init__()
		self.music_folders = music_folders
		self.temp_added_folders = []

	async def update_music_folders(self) -> None:
		music_folders_widgets = self.query_one("#music-folders", VerticalScroll)
		await music_folders_widgets.remove_children()

		for folder in self.music_folders:
			music_folders_widgets.mount(Checkbox(folder.folder_path, folder.is_checked,
											classes="folder-checkbox",
											id="folder-checkbox-{}".format(calculate_hash(folder.folder_path, True))))
			
		for folder in self.temp_added_folders:
			music_folders_widgets.mount(Checkbox(folder, True,
											classes="folder-checkbox",
											id="folder-checkbox-{}".format(calculate_hash(folder, True))))

	async def on_mount(self) -> None:
		await self.update_music_folders()

	def compose(self) -> ComposeResult:
		with Container(id="scan-folders-widget"):
			yield Static("Scan for files...")
			yield VerticalScroll(id="music-folders")
			with Horizontal(classes="dialog-buttons"):
				yield Button("Choose Folder", variant="success", id="btn-folder-selection")
				yield Button("Scan", variant="success", id="btn-scan-yes")
				yield Button("Cancel", variant="error", id="btn-scan-cancel")

	@on(Button.Pressed, "#btn-folder-selection")
	def on_folder_selection(self) -> None:

		async def selected_folders(folder_path: str | None) -> None:
			if folder_path is not None:
				if os.path.isdir(folder_path):
					if any(str(folder_path) in folder.folder_path for folder in self.music_folders):
						return

					if folder_path not in self.temp_added_folders:
						self.temp_added_folders.append(str(folder_path) + "/")
					await self.update_music_folders()

		self.app.push_screen(FolderDialog(), selected_folders)

	@on(Button.Pressed, "#btn-scan-yes")
	def on_confirm(self) -> None:
		updated_music_folders = []

		for folder in self.music_folders:
			checkbox = self.query_one("#folder-checkbox-{}".format(calculate_hash(folder.folder_path, True)))
			updated_music_folders.append({"folder_path": folder.folder_path, "checked": checkbox.value})

		for folder_path in self.temp_added_folders:
			checkbox = self.query_one("#folder-checkbox-{}".format(calculate_hash(folder_path, True)))
			updated_music_folders.append({"folder_path": folder_path, "checked": checkbox.value})
		
		self.temp_added_folders.clear()
		self.dismiss(updated_music_folders)

	@on(Button.Pressed, "#btn-scan-cancel")
	def on_cancel(self) -> None:
		self.temp_added_folders.clear()
		self.dismiss(None)

# --- Delete File Popup -------------------------------------------------------

class DeleteFilePopup(ModalScreen[bool]):

	DEFAULT_CSS = """
	DeleteFilePopup {
		align: center middle;
	}
	"""

	def __init__(self, msg: str) -> None:
		super().__init__()
		self.msg = msg

	def compose(self) -> ComposeResult:
		with Container(id="delete-popup"):
			yield Static("[bold red]Delete File?[/bold red]", id="file-popup-title")
			yield Static(self.msg)
			with Horizontal(classes="dialog-buttons"):
				yield Button("Yes", variant="success", id="btn-delete-yes")
				yield Button("Cancel", variant="error", id="btn-delete-cancel")

	@on(Button.Pressed, "#btn-delete-yes")
	def on_confirm(self) -> None:
		self.dismiss(True)

	@on(Button.Pressed, "#btn-delete-cancel")
	def on_cancel(self) -> None:
		self.dismiss(False)

# --- Add To Playlist Popup -------------------------------------------------------

class AddToPlaylistPopup(ModalScreen[dict | None]):

	DEFAULT_CSS = """
	AddToPlaylistPopup {
		align: center middle;
	}
	"""

	def __init__(self, song_playlists: list) -> None:
		super().__init__()
		self.song_playlists = song_playlists

	def on_mount(self) -> None:
		add_to_playlist_popup = self.query_one("#add-to-playlist-popup", Container)
		add_to_playlist_popup.border_title = "Playlists"
		selection_list = self.query_one("#playlists-ls", SelectionList)
		for playlist in self.song_playlists:
			if not playlist.is_auto_playlist:
				selection_list.add_option((playlist.playlist_name, playlist.playlist_id, playlist.in_playlist))

	def compose(self) -> ComposeResult:
		with Container(id="add-to-playlist-popup"):
			yield SelectionList[int](id="playlists-ls")
			with Horizontal(classes="dialog-buttons"):
				yield Button("Update", variant="success", id="update-to-playlist-yes")
				yield Button("Cancel", variant="error", id="update-to-playlist-no")

	@on(Button.Pressed, "#update-to-playlist-yes")
	def on_confirm(self) -> dict:
		selection_ls = self.query_one("#playlists-ls", SelectionList)
		selected = list(selection_ls.selected)
		results = {}
		for option in selection_ls.options:
			results[option.value] = option.value in selected	# [{"playlist_id": selected}]
		self.dismiss(results)

	@on(Button.Pressed, "#update-to-playlist-no")
	def on_cancel(self) -> None:
		self.dismiss(None)	

# --- Song Sub-menu -----------------------------------------------------------

class SongSubMenu(ModalScreen[SongMenuResult | None]):

	DEFAULT_CSS = """
	SongSubMenu {
		align: center middle;
	}
	"""

	def __init__(self, song_info: SongInfo, song_playlists: list, is_from_library: list,
			  		is_auto_playlist: list = False) -> None:
		super().__init__()
		self.song_info = song_info
		self.song_playlists = song_playlists
		self.is_from_library = is_from_library
		self.is_auto_playlist = is_auto_playlist

	def on_mount(self) -> None:
		song_submenu = self.query_one("#options-submenu", OptionList)
		song_submenu.border_title = "Song Submenu"

	def compose(self) -> ComposeResult:
		options = [
			Option("Play Now", id="opt-play"),
			Option("Edit", id="opt-edit"),
			Option("Include in Playlist ▶", id="opt-playlists"),
		]

		if not self.is_auto_playlist:
			options.append(
				Option("Remove", id="opt-remove")
			)

		yield OptionList(
			*options,
			id="options-submenu"
		)

	@on(OptionList.OptionSelected, "#options-submenu")
	def option_selected(self, event: OptionList.OptionSelected) -> None:
		option = event.option_list.get_option_at_index(event.option_index)

		if option.id == "opt-play":
			self.dismiss(SongMenuResult(SongAction.PLAY))
		elif option.id == "opt-edit":
			def edit_song(song: SongInfo | None) -> None:
				if song:
					self.dismiss(SongMenuResult(SongAction.EDIT, song))
				else:
					self.dismiss(None)

			self.app.push_screen(EditSongInfo(self.song_info), edit_song)
		elif option.id == "opt-playlists":
			def add_to_playlist(results: dict | None) -> None:
				if results:
					self.dismiss(SongMenuResult(SongAction.UPDATE_TO_PLAYLIST, results))
				else:
					self.dismiss(None)

			self.app.push_screen(AddToPlaylistPopup(self.song_playlists), add_to_playlist)
		elif option.id == "opt-remove":
			def confirm_remove(confirmed: bool) -> None:
				if confirmed and self.is_from_library:
					self.dismiss(SongMenuResult(SongAction.DELETE))
				elif confirmed:
					self.dismiss(SongMenuResult(SongAction.REMOVE))
				else:
					self.dismiss(None)

			prompt = "Do you wish to remove this song from this playlist?"
			if self.is_from_library:
				prompt = "Are you sure you want to delete this song?"
			self.app.push_screen(ConfirmDialog(prompt), confirm_remove)

	@on(Click)
	def click_background(self, event: Click) -> None:
		song_submenu = self.query_one("#options-submenu")

		# Ignore clicks inside this popup
		if song_submenu in event.widget.ancestors_with_self:
			return

		self.dismiss(None)

# --- Edit Song Info ----------------------------------------------------------

class EditSongInfo(ModalScreen[SongInfo | None]):

	DEFAULT_CSS = """
	EditSongInfo {
		align: center middle;
	}
	"""

	def __init__(self, song: SongInfo) -> None:
		super().__init__()
		self.song_info = song

	def on_mount(self) -> None:
		container = self.query_one("#song-editor", Container)
		container.border_title = "Edit Song Info"
		input_title = self.query_one("#edit-title-input", Input)
		input_title.value = self.song_info.title
		input_artist = self.query_one("#edit-artist-input", Input)
		input_artist.value = self.song_info.artist
		input_album = self.query_one("#edit-album-input", Input)
		input_album.value = self.song_info.album
		input_genres = self.query_one("#edit-genres-input", Input)
		input_genres.value = self.song_info.genres

	def compose(self) -> ComposeResult:
		with Container(id="song-editor"):
			with Vertical(classes="group-song-edit"):
				yield Label("Title:")
				yield Input(id="edit-title-input")
			with Vertical(classes="group-song-edit"):
				yield Label("Artist:")
				yield Input(id="edit-artist-input")
			with Vertical(classes="group-song-edit"):
				yield Label("Album:")
				yield Input(id="edit-album-input")
			with Vertical(classes="group-song-edit"):
				yield Label("Genre:")
				yield Input(id="edit-genres-input")
			with Horizontal(classes="dialog-buttons"):
				yield Button("Save", variant="success", id="edit-save")
				yield Button("Cancel", variant="error", id="edit-cancel")

	@on(Input.Changed, "#edit-title-input")
	def changed_title_input(self, event: Input.Changed) -> None:
		self.song_info.title = event.value

	@on(Input.Changed, "#edit-artist-input")
	def changed_artist_input(self, event: Input.Changed) -> None:
		self.song_info.artist = event.value

	@on(Input.Changed, "#edit-album-input")
	def changed_album_input(self, event: Input.Changed) -> None:
		self.song_info.album = event.value

	@on(Input.Changed, "#edit-genres-input")
	def changed_genres_input(self, event: Input.Changed) -> None:
		self.song_info.genres = event.value

	@on(Button.Pressed, "#edit-save")
	def on_save(self) -> None:
		genres_ls = [genre.strip().lower() for genre in self.song_info.genres.split(";")]
		self.song_info.genres = ";".join(genres_ls)
		self.dismiss(self.song_info)

	@on(Button.Pressed, "#edit-cancel")
	def on_cancel(self) -> None:
		self.dismiss(None)

# --- Create New Playlist -----------------------------------------------------

class NewPlaylistPopup(ModalScreen[None]):

	DEFAULT_CSS = """
	NewPlaylistPopup {
		align: center middle;
	}
	"""

	def __init__(self) -> None:
		super().__init__()
		self.playlist_name = ""
		self.advanced_filter = ""

	def on_mount(self) -> None:
		container = self.query_one("#new-playlist-popup", Container)
		container.border_title = "Create New Playlist"
		advanced_filter_label = self.query_one("#advanced-filter-label", Label)
		advanced_filter_label.visible = False
		advanced_filter_input = self.query_one("#advanced-filter", Input)
		advanced_filter_input.visible = False

	def compose(self) -> ComposeResult:
		with Container(id="new-playlist-popup"):
			with Vertical(classes="playlist-name"):
				yield Label("Playlist name:")
				yield Input(id="playlist-name-input")
				yield Checkbox("Autoplaylist", id="autoplaylist-checkbox")
				yield Label("Advanced Filter:", id="advanced-filter-label")
				yield Input(id="advanced-filter", placeholder="e.g. genre:\"rap\" AND artist=\"tlinh\"")
			with Horizontal(classes="dialog-buttons"):
				yield Button("Create", variant="success", id="new-playlist-create")
				yield Button("Cancel", variant="error", id="new-playlist-cancel")

	@on(Checkbox.Changed, "#autoplaylist-checkbox")
	def changed_autoplaylist_checkbox(self, event: Checkbox.Changed) -> None:
		checkbox = self.query_one("#autoplaylist-checkbox", Checkbox)
		is_auto_playlist = checkbox.value
		advanced_filter_input = self.query_one("#advanced-filter", Input)
		advanced_filter_label = self.query_one("#advanced-filter-label", Label)
		if is_auto_playlist:
			advanced_filter_input.visible = True
			advanced_filter_label.visible = True
		else:
			advanced_filter_input.visible = False
			advanced_filter_label.visible = False

	@on(Input.Changed, "#playlist-name-input")
	def changed_playlist_name_input(self, event: Input.Changed) -> None:
		self.playlist_name = event.value

	@on(Input.Changed, "#advanced-filter")
	def changed_advanced_filter_input(self, event: Input.Changed) -> None:
		self.advanced_filter = event.value

	@on(Button.Pressed, "#new-playlist-create")
	def on_create_new_playlist(self) -> None:
		checkbox = self.query_one("#autoplaylist-checkbox", Checkbox)
		is_auto_playlist = checkbox.value

		self.dismiss({"playlist_name": self.playlist_name,
						"is_auto_playlist": is_auto_playlist,
						"advanced_filter": self.advanced_filter})

	@on(Button.Pressed, "#new-playlist-cancel")
	def on_cancel_new_playlist(self) -> None:
		self.dismiss(None)

# --- Playlist Submenu --------------------------------------------------------
class PlaylistSubMenu(ModalScreen[SongMenuResult | None]):

	DEFAULT_CSS = """
	PlaylistSubMenu {
		align: center middle;
	}
	"""

	def __init__(self, playlist_name: str, advanced_filter: str) -> None:
		super().__init__()
		self.playlist_name = playlist_name
		self.advanced_filter = advanced_filter

	def on_mount(self) -> None:
		playlist_submenu = self.query_one("#playlist-submenu", OptionList)
		playlist_submenu.border_title = "Playlist Submenu"

	def compose(self) -> ComposeResult:
		yield OptionList(
			Option("Edit", id="opt-playlist-edit"),
			Option("Delete", id="opt-playlist-delete"),
			id="playlist-submenu"
		)

	@on(OptionList.OptionSelected, "#playlist-submenu")
	def option_selected(self, event: OptionList.OptionSelected) -> None:
		option = event.option_list.get_option_at_index(event.option_index)

		if option.id == "opt-playlist-edit":
			def edit_playlist(result: dict | None) -> None:
				if result:
					self.dismiss(PlaylistMenuResult(PlaylistAction.EDIT, result))
				else:
					self.dismiss(None)

			self.app.push_screen(EditPlaylistPopup(self.playlist_name, self.advanced_filter), edit_playlist)
		elif option.id == "opt-playlist-delete":
			def confirm_remove(confirmed: bool) -> None:
				if confirmed:
					self.dismiss(PlaylistMenuResult(PlaylistAction.DELETE))
				else:
					self.dismiss(None)

			prompt = "Do you wish to delete this playlist?"
			self.app.push_screen(ConfirmDialog(prompt), confirm_remove)

	@on(Click)
	def click_background(self, event: Click) -> None:
		playlist_submenu = self.query_one("#playlist-submenu")

		# Ignore clicks inside this popup
		if playlist_submenu in event.widget.ancestors_with_self:
			return

		self.dismiss(None)

# --- Edit Playlist Popup ---------------------------------------------------------

class EditPlaylistPopup(ModalScreen[None]):

	DEFAULT_CSS = """
	EditPlaylistPopup {
		align: center middle;
	}
	"""

	def __init__(self, playlist_name: str, advanced_filter: str) -> None:
		super().__init__()
		self.playlist_name = playlist_name
		self.advanced_filter = advanced_filter

	def on_mount(self) -> None:
		container = self.query_one("#edit-playlist-popup", Container)
		container.border_title = "Edit Playlist"

		advanced_filter_label = self.query_one("#advanced-filter-label", Label)
		advanced_filter_input = self.query_one("#advanced-filter", Input)
		advanced_filter_input.value = self.advanced_filter
		if self.advanced_filter == "":
			advanced_filter_label.visible = False
			advanced_filter_input.visible = False
		
		playlist_input = self.query_one("#playlist-name-input", Input)
		playlist_input.value = self.playlist_name

	def compose(self) -> ComposeResult:
		with Container(id="edit-playlist-popup"):
			with Vertical(classes="playlist-name"):
				yield Label("Playlist name:")
				yield Input(id="playlist-name-input")
				yield Label("Advanced Filter:", id="advanced-filter-label")
				yield Input(id="advanced-filter")
			with Horizontal(classes="dialog-buttons"):
				yield Button("Save", variant="success", id="playlist-save")
				yield Button("Cancel", variant="error", id="playlist-cancel")

	@on(Input.Changed, "#playlist-name-input")
	def changed_playlist_name_input(self, event: Input.Changed) -> None:
		self.playlist_name = event.value

	@on(Input.Changed, "#advanced-filter")
	def changed_advanced_filter_input(self, event: Input.Changed) -> None:
		self.advanced_filter = event.value

	@on(Button.Pressed, "#playlist-save")
	def on_create_new_playlist(self) -> None:

		self.dismiss({"playlist_name": self.playlist_name, "advanced_filter": self.advanced_filter})

	@on(Button.Pressed, "#playlist-cancel")
	def on_cancel_new_playlist(self) -> None:
		self.dismiss(None)

# --- Error Popup ----------------------------------------------------------

class ErrorPopup(ModalScreen[bool]):

	DEFAULT_CSS = """
	ErrorPopup {
		align: center middle;
	}
	"""

	def __init__(self, message: str) -> None:
		super().__init__()
		self.message = message

	def compose(self) -> ComposeResult:
		with Container(id="confirm-dialog"):
			yield Static(self.message)
			with Horizontal(classes="dialog-buttons"):
				yield Button("Ok", variant="success", id="confirm-ok")

	@on(Button.Pressed, "#confirm-ok")
	def on_confirm(self) -> None:
		self.dismiss(True)
