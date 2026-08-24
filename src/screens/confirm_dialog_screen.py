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