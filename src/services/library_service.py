from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.flac import FLAC

from database.sql_connector import SQL_Connector

from models.abstract_syntax_tree import Node
from models.music_folders import MusicFoldersInfo
from models.playlist import PlaylistInfo
from models.song import SongInfo

from utils.hashing import calculate_hash
from utils.search_filter import build_music_query

import os

class LibaryService:
	def __init__(self):
		self.sql_db_connector = SQL_Connector()

	def get_all_songs(self) -> list[SongInfo]:
		results = self.sql_db_connector.get_all_songs()
		all_songs = []
		for song in results:
			all_songs.append(SongInfo(song["id"], song["title"], song["artist"],
							 	song["album"], song["genres"], song["duration_ms"],
								song["file_path"]))
		return all_songs

	def add_playlist(self, playlist_name: str, is_auto_playlist: int, advanced_filter: str) -> None:
		self.sql_db_connector.add_playlist(playlist_name, is_auto_playlist, advanced_filter)

	def get_playlist(self, playlist_name: str) -> PlaylistInfo:
		result = self.sql_db_connector.get_playlist(playlist_name)
		return PlaylistInfo(result["id"], result["playlist_name"],
					  result["is_auto_playlist"], result["advanced_filter"])

	def update_playlist(self, playlist_id: int, playlist_name: str, advanced_filter: str) -> None:
		self.sql_db_connector.update_playlist(playlist_id, playlist_name, advanced_filter)

	def delete_playlist(self, playlist_id: int) -> None:
		self.sql_db_connector.delete_playlist(playlist_id)
	
	def get_playlists(self) -> list[PlaylistInfo]:
		results = self.sql_db_connector.get_all_playlists()
		playlists = []
		for playlist in results:
			playlists.append(PlaylistInfo(playlist["id"], playlist["playlist_name"],
					  			playlist["is_auto_playlist"], playlist["advanced_filter"]))
		return playlists
	
	def get_playlist_songs(self, playlist_name) -> list[SongInfo]:
		results = self.sql_db_connector.get_songs_in_playlist(playlist_name)
		songs = []
		for song in results:
			songs.append(SongInfo(song["id"], song["title"], song["artist"],
							 	song["album"], song["genres"], song["duration_ms"],
								song["file_path"]))
		return songs
	
	def add_music_folder(self, folder_path: str) -> None:
		self.sql_db_connector.add_folder(folder_path, True)

	def remove_music_folder(self, folder_path: str) -> None:
		self.sql_db_connector.remove_folder(folder_path)
	
	def get_music_folders(self) -> list[MusicFoldersInfo]:
		results = self.sql_db_connector.get_folders()
		folders = []
		for result in results:
			folders.append(MusicFoldersInfo(result["id"], result["folder_path"], result["is_checked"]))
		return folders
	
	def check_folder_exists(self, folder_path: str) -> bool:
		return self.sql_db_connector.check_folder_exists(folder_path)

	def add_song(self, title: str, artist: str, album: str, genres: str,
			  		duration_ms: int, file_path: str, file_hash: str) -> None:
		self.sql_db_connector.add_song(title, artist, album, genres, duration_ms, file_path, file_hash)

	def get_song(self, id: int) -> SongInfo:
		song = self.sql_db_connector.get_song(id)
		return SongInfo(song["id"], song["title"], song["artist"], song["album"],
				  	song["genres"], song["duration_ms"], song["file_path"])

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

	def get_playlists_for_song(self, song_id: int, playlists: list[PlaylistInfo]) -> dict:
		results_dict = {}
		
		for playlist in playlists:
			in_playlist = self.sql_db_connector.is_song_in_playlist(song_id, playlist.id)
			results_dict[playlist.id] = in_playlist
		return results_dict
	
	def add_songs_from_folder(self, path) -> int:
		all_files = os.listdir(f"{path}")
		added_num_songs = 0

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
					added_num_songs += 1
			else:
				curr_path += ("/" if "/" in curr_path else "\\")
				if os.path.isdir(curr_path):
					all_files = os.listdir(curr_path)
					for file_path in all_files:
						stack.append(Node(curr_path, file_path))

		return added_num_songs

	def scan_music_folders(self, music_folders: list) -> int:
		num_new_songs = 0
		for folder in music_folders:
			if folder["checked"] == True:
				if not self.check_folder_exists(folder["folder_path"]):
					self.add_music_folder(folder["folder_path"])
				num_new_songs += self.add_songs_from_folder(folder["folder_path"])
			elif self.check_folder_exists(folder["folder_path"]) and folder["checked"] == False:
				self.remove_music_folder(folder["folder_path"])

		return num_new_songs

	def get_playlist_advanced_filter(self, filter_text: str) -> list[SongInfo]:
		sql, parameters = build_music_query(filter_text)
		results = self.sql_db_connector.search_music(sql, parameters)
		songs = []
		for song in results:
			songs.append(SongInfo(song["id"], song["title"], song["artist"],
							 	song["album"], song["genres"], song["duration_ms"],
								song["file_path"]))
		return songs
