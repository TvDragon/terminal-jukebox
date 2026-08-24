def make_bar(current: int, max: int, width: int) -> str:
	if max != 0:
		ratio = current / max
		filled = int(ratio * width)
		empty = width - filled
		return f"[{'█' * filled}{'-' * empty}]"

	return f"[{'-' * width}]"

def make_progress_bar_timer(current: int, duration: int, width: int=50) -> str:
	bar = make_bar(current, duration, width)
	progress_bar = "{}:{:02d} {} {}:{:02d}".format(int(current / 60),
													int(current % 60),
													bar,
													int(duration / 60),
													int(duration % 60))
	return progress_bar

def render_volume_bar(volume: int) -> str:
	total = 20

	filled = int((volume / 100) * total)
	empty = total - filled

	return (
			"[bold]🔊[/bold]"
			f"[green]{'─' * (filled - 1)}[green]"
			"[bold green]\u25a0[/bold green]"
			f"[grey]{'─' * empty}[grey]"
			f" {volume}%"
		)