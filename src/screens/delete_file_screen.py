from textual import on
from textual.app import ComposeResult
from textual.containers import (
	Container,
	Horizontal,
)
from textual.screen import ModalScreen
from textual.widgets import (
	Button,
	Static,
)

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