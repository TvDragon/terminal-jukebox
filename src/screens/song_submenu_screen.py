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
	SelectionList,
)

from models.song_menu_result import SongAction, SongMenuResult
from models.song import SongInfo

from screens.confirm_dialog_screen import ConfirmDialog

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