from textual import on
from textual.app import ComposeResult
from textual.containers import (
	Container,
	Horizontal,
	Vertical,
)
from textual.events import Click
from textual.widgets.option_list import Option
from textual.screen import ModalScreen
from textual.widgets import (
	Button,
	Input,
	Label,
	OptionList,
)

from models.playlist_menu_result import PlaylistAction, PlaylistMenuResult
from models.song_menu_result import SongMenuResult

from screens.confirm_dialog_screen import ConfirmDialog

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