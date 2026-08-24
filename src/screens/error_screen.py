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