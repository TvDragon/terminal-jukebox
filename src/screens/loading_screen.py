from textual.app import ComposeResult
from textual.containers import (
	Vertical,
)
from textual.screen import ModalScreen
from textual.widgets import (
	Label,
	LoadingIndicator,
)

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