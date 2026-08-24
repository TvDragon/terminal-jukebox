from textual import on
from textual.app import ComposeResult
from textual.containers import (
	Container,
	Horizontal,
	Vertical,
)
from textual.screen import ModalScreen
from textual.widgets import (
	Button,
	Checkbox,
	Input,
	Label,
)

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