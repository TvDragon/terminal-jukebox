from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.flac import FLAC

from models.model import Node
from services.database_handler import SQL_Connector

from utils import calculate_hash

import os

class LibaryService:
	def __init__(self):
		self.sql_db_connector = SQL_Connector()

	def get_all_songs(self) -> list:
		return self.sql_db_connector.get_all_songs()

	def add_playlist(self, playlist_name: str, is_auto_playlist: int) -> None:
		self.sql_db_connector.add_playlist(playlist_name, is_auto_playlist)

	def update_playlist(self, playlist_id: int, playlist_name: str) -> None:
		self.sql_db_connector.update_playlist(playlist_id, playlist_name)

	def delete_playlist(self, playlist_id: int) -> None:
		self.sql_db_connector.delete_playlist(playlist_id)
	
	def get_playlists(self) -> list:
		return self.sql_db_connector.get_all_playlists()
	
	def get_playlist_songs(self, playlist_name) -> list:
		return self.sql_db_connector.get_songs_in_playlist(playlist_name)
	
	def add_music_folder(self, folder_path: str) -> None:
		self.sql_db_connector.add_folder(folder_path, True)

	def remove_music_folder(self, folder_path: str) -> None:
		self.sql_db_connector.remove_folder(folder_path)
	
	def get_music_folders(self) -> list:
		return self.sql_db_connector.get_folders()
	
	def check_folder_exists(self, folder_path: str) -> bool:
		return self.sql_db_connector.check_folder_exists(folder_path)

	def add_song(self, title: str, artist: str, album: str, genres: str,
			  		duration_ms: int, file_path: str, file_hash: str) -> None:
		self.sql_db_connector.add_song(title, artist, album, genres, duration_ms, file_path, file_hash)

	def get_song(self, id: int) -> object:
		return self.sql_db_connector.get_song(id)

	def edit_song(self, id: int, title: str, artist: str, album: str, genres: str, file_path: str) -> None:
		success = self.sql_db_connector.edit_song(id, title, artist, album, genres)

		if success:
			audio = EasyID3(file_path)
			audio["title"] = title
			audio["artist"] = artist
			audio["album"] = album
			ls_genres = genres.split(";")
			audio["genre"] = ls_genres
			audio.save(file_path)

	def delete_song(self, song_id: int) -> None:
		self.sql_db_connector.remove_song(song_id)

	def check_song_exists(self, file_hash: str) -> bool:
		return self.sql_db_connector.check_song_exists(file_hash)
	
	def add_song_to_playlist(self, song_id: int, playlist_id: int) -> None:
		self.sql_db_connector.add_song_to_playlist(song_id, playlist_id)

	def remove_song_from_playlist(self, song_id: int, playlist_id: int) -> None:
		self.sql_db_connector.remove_song_from_playlist(song_id, playlist_id)

	def get_playlists_for_song(self, song_id: int, playlists: list) -> dict:
		results_dict = {}
		
		for playlist in playlists:
			in_playlist = self.sql_db_connector.is_song_in_playlist(song_id, playlist["id"])
			results_dict[playlist["id"]] = in_playlist
		return results_dict
	
	def add_songs_from_folder(self, path) -> None:
		all_files = os.listdir(f"{path}")

		visited = set()
		stack = []
		for file_path in all_files:
			stack.append(Node(path, file_path))

		while len(stack) > 0:
			node = stack.pop()
			curr_path = node.parent + node.name

			if curr_path in visited:
				continue

			visited.add(curr_path)

			if curr_path.endswith(".mp3") or curr_path.endswith(".flac"):
				audio = EasyID3(curr_path)
				audio_file = None
				if curr_path.endswith(".flac"):
					audio_file = FLAC(curr_path)
				elif curr_path.endswith(".mp3"):
					audio_file = MP3(curr_path)
				
				info = f"No Metadata: {curr_path}"
				if "title" in audio:
					info = f"Title: {audio["title"]}"
				if "genre" in audio:
					info += f" - Genre: {audio["genre"]}"
				if info.startswith("No Metadata"):
					print(info)

				title = ""
				artist = ""
				album = ""
				genres = ""
				duration = int(audio_file.info.length * 1000)
				file_path = curr_path
				file_hash = calculate_hash(file_path)
				if "title" in audio:
					title = audio["title"][0]
				if "artist" in audio:
					artist = audio["artist"][0]
				if "album" in audio:
					album = audio["album"][0]
				if "genre" in audio:
					genres_list = audio["genre"]
					for genre in genres_list:
						genres += "{};".format(genre)
					genres = genres[0:len(genres) - 1]

				if not self.check_song_exists(file_hash):
					self.add_song(title, artist, album, genres, duration, file_path, file_hash)
			else:
				curr_path += "/"
				if os.path.isdir(curr_path):
					all_files = os.listdir(curr_path)
					for file_path in all_files:
						stack.append(Node(curr_path, file_path))