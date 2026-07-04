from textual import on
from textual.app import ComposeResult
from textual.containers import (
	Container,
	Horizontal,
	VerticalScroll
)
from textual.events import Click
from textual.widgets.option_list import Option
from textual.screen import ModalScreen
from textual.widgets import (
	Button,
	Checkbox,
	DirectoryTree,
	OptionList,
	SelectionList,
	Static,
)
from textual.widgets.selection_list import Selection

from models.model import SongAction, SongMenuResult
from utils import calculate_hash

import os

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
			yield DirectoryTree("./", id="folder-tree")
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

	def __init__(self, music_folders) -> None:
		super().__init__()
		self.music_folders = music_folders
		self.temp_added_folders = []

	async def update_music_folders(self) -> None:
		music_folders_widgets = self.query_one("#music-folders", VerticalScroll)
		await music_folders_widgets.remove_children()

		for folder in self.music_folders:
			music_folders_widgets.mount(Checkbox(folder["folder_path"], folder["is_checked"],
											classes="folder-checkbox",
											id="folder-checkbox-{}".format(calculate_hash(folder["folder_path"], True))))
			
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
					if any(str(folder_path) in folder["folder_path"] for folder in self.music_folders):
						return

					if folder_path not in self.temp_added_folders:
						self.temp_added_folders.append(str(folder_path) + "/")
					await self.update_music_folders()

		self.app.push_screen(FolderDialog(), selected_folders)

	@on(Button.Pressed, "#btn-scan-yes")
	def on_confirm(self) -> list:
		updated_music_folders = []

		for folder in self.music_folders:
			checkbox = self.query_one("#folder-checkbox-{}".format(calculate_hash(folder["folder_path"], True)))
			updated_music_folders.append({"folder_path": folder["folder_path"], "checked": checkbox.value})

		for folder_path in self.temp_added_folders:
			checkbox = self.query_one("#folder-checkbox-{}".format(calculate_hash(folder_path, True)))
			updated_music_folders.append({"folder_path": folder_path, "checked": checkbox.value})
		
		self.temp_added_folders.clear()
		self.dismiss(updated_music_folders)

	@on(Button.Pressed, "#btn-scan-cancel")
	def on_cancel(self) -> None:
		self.temp_added_folders.clear()
		self.dismiss(None)

# --- Delete File Popup ----------------------------------------------------

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

# --- Playlist Sub-menu ----------------------------------------------------

class PlaylistSubMenu(ModalScreen[list]):

	DEFAULT_CSS = """
	PlaylistSubMenu {
		align: center middle;
	}
	"""

	def __init__(self, playlists: list) -> None:
		super().__init__()
		self.playlists = playlists

	def on_mount(self) -> None:
		selection_list = self.query_one("#playlists-ls", SelectionList)
		selection_list.border_title = "Playlists"
		for playlist in self.playlists:
			if not playlist["is_auto_playlist"]:
				# TODO: Show checked if it is already in that playlist
				selection_list.add_option((playlist["playlist_name"], playlist["id"]))

	def compose(self) -> ComposeResult:
		with Container(id="folder-dialog"):
			yield SelectionList[int](id="playlists-ls")
			with Horizontal(classes="dialog-buttons"):
				yield Button("Add", variant="success", id="add-to-playlist-yes")
				yield Button("Cancel", variant="error", id="add-to-playlist-no")

	@on(Button.Pressed, "#add-to-playlist-yes")
	def on_confirm(self) -> (str | None):
		sel = self.query_one("#playlists-ls", SelectionList)
		selected = list(sel.selected)
		self.dismiss(selected)

	@on(Button.Pressed, "#add-to-playlist-no")
	def on_cancel(self) -> None:
		self.dismiss([])	

# --- Song Sub-menu -----------------------------------------------------

class SongSubMenu(ModalScreen[SongMenuResult | None]):

	DEFAULT_CSS = """
	SongSubMenu {
		align: center middle;
	}
	"""

	def __init__(self, song_id: int, song_title: str, playlists: list) -> None:
		super().__init__()
		self.song_id = song_id
		self.song_title = song_title
		self.playlists = playlists

	def compose(self) -> ComposeResult:
		with Container(id="song-sub-menu"):
			yield OptionList(
				Option("Play Now", id="opt-play"),
				Option("Edit", id="opt-edit"),
				Option("Include in Playlist ▶", id="opt-playlists"),
				Option("Delete", id="opt-delete"),
				id="options-sub-menu"
			)

	@on(OptionList.OptionSelected, "#options-sub-menu")
	def option_selected(self, event: OptionList.OptionSelected) -> None:
		option = event.option_list.get_option_at_index(event.option_index)

		if option.id == "opt-play":
			self.dismiss(SongMenuResult(SongAction.PLAY))
		elif option.id == "opt-edit":
			pass
		elif option.id == "opt-playlists":
			def add_to_playlist(results: list) -> None:
				if len(results) != 0:
					self.dismiss(SongMenuResult(SongAction.ADD_TO_PLAYLIST, results))
				else:
					self.dismiss(None)

			self.app.push_screen(PlaylistSubMenu(self.playlists), add_to_playlist)
		elif option.id == "opt-delete":
			def confirm_delete(confirmed: bool) -> None:
				if confirmed:
					self.dismiss(SongMenuResult(SongAction.DELETE))
				else:
					self.dismiss(None)

			self.app.push_screen(ConfirmDialog("Are you sure you want to delete this song?"), confirm_delete)

	@on(Click)
	def click_background(self, event: Click) -> None:
		song_submenu = self.query_one("#song-sub-menu")

		# Ignore clicks inside this popup
		if song_submenu in event.widget.ancestors_with_self:
			return

		self.dismiss(None)