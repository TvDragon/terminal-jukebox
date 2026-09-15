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

class InfoDialog(ModalScreen[bool]):
	"""A modal information dialog."""

	DEFAULT_CSS = """
	InfoDialog {
		align: center middle;
	}
	"""

	def __init__(self, message: str) -> None:
		super().__init__()
		self.message = message

	def compose(self) -> ComposeResult:
		with Container(id="confirm-dialog"):
			yield Static(self.message, id="msg-static")
			with Horizontal(classes="dialog-buttons"):
				yield Button("Ok", variant="success", id="ok-yes")

	@on(Button.Pressed, "#ok-yes")
	def on_ok(self) -> None:
		self.dismiss(True)