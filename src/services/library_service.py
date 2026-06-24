from services.database_handler import SQL_Connector

class LibaryService:
	def __init__(self):
		self.sql_db_connector = SQL_Connector()

	def get_all_songs(self) -> list:
		return self.sql_db_connector.get_all_songs()
	
	def get_playlists(self) -> list:
		return self.sql_db_connector.get_all_playlists()
	
	def get_playlist_songs(self, playlist_name) -> list:
		return self.sql_db_connector.get_songs_in_playlist(playlist_name)
	
	def add_music_folder(self, folder_path: str) -> None:
		self.sql_db_connector.add_folder(folder_path, True)

	def remove_music_folder(self, folder_path: str) -> None:
		self.sql_db_connector.remove_folder(folder_path)
		self.sql_db_connector.remove_songs_from_folder(folder_path)
	
	def get_music_folders(self) -> list:
		return self.sql_db_connector.get_folders()
	
	def check_folder_exists(self, folder_path: str) -> bool:
		return self.sql_db_connector.check_folder_exists(folder_path)

	def add_song(self, title: str, artist: str, album: str, genres: str,
			  		duration_ms: int, file_path: str, file_hash: str) -> None:
		self.sql_db_connector.add_song(title, artist, album, genres, duration_ms, file_path, file_hash)

	def check_song_exists(self, file_hash: str) -> bool:
		return self.sql_db_connector.check_song_exists(file_hash)