from just_playback import Playback

class MusicPlayer:
	def __init__(self):
		self.playback = Playback()
		self.volume = 40
		self.song_idx = -1
		self.is_playing = False
		self.current_position = 0
		self.duration = 0
		self.playback.set_volume(self.volume / 100)

	def get_volume(self) -> int:
		return self.volume

	def increase_volume(self, inc_vol: int) -> None:
		self.volume += inc_vol
		if self.volume > 100:
			self.volume = 100
		self.playback.set_volume(self.volume / 100)

	def decrease_volume(self, dec_vol: int) -> None:
		self.volume -= dec_vol
		if self.volume < 0:
			self.volume = 0
		self.playback.set_volume(self.volume / 100)

	def set_play(self) -> None:
		self.is_playing = True

	def play(self) -> None:
		self.playback.play()
		self.playback.seek(self.current_position)
		self.is_playing = True

	def stop_play(self) -> None:
		self.is_playing = False

	def pause(self) -> None:
		self.playback.pause()
		self.is_playing = False

	def update_position(self) -> None:
		self.current_position += 1

	def get_is_playing(self) -> None:
		return self.is_playing
	
	def get_current_song_position(self) -> int:
		return self.current_position
	
	def get_song_duration(self) -> int:
		return self.duration

	def reset_song_idx(self) -> None:
		self.song_idx = 0

	def set_song_idx(self, idx: int) -> None:
		self.song_idx = idx

	def prev_song_idx(self) -> None:
		self.song_idx -= 1

	def next_song_idx(self) -> None:
		self.song_idx += 1

	def get_song_idx(self) -> int:
		return self.song_idx
	
	def load_song(self, song) -> None:
		self.current_position = 0
		self.playback.load_file(song["file_path"])
		self.duration = int(song["duration_ms"] / 1000)