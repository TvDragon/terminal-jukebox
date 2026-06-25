from textual import on
from textual.app import ComposeResult
from textual.containers import (
	Container,
	Horizontal,
	VerticalScroll
)
from textual.screen import ModalScreen
from textual.widgets import (
	Button,
	Checkbox,
	DirectoryTree,
	Static,
)

from utils import calculate_hash

import os

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
					if str(folder_path) in self.music_folders:
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