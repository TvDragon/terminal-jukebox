import sqlite3
import os

class SQL_Connector:
	def __init__(self, database="./music-library.db"):
		flag = os.path.isfile(database)

		# Create connection to database
		self.db_conn = sqlite3.connect(database, check_same_thread=False)
		self.db_conn.row_factory = sqlite3.Row	# Query results behave like dictionaries
		# Enforce foreign key constraints to prevent invalid foreign keys being used
		self.db_conn.execute("PRAGMA foreign_keys = ON")

		# Create a cursor
		self.db_cursor = self.db_conn.cursor()

		if flag == False:
			self.database_setup()

	def database_setup(self) -> None:
		# Clear the database if needed
		if not self.execute("DROP TABLE IF EXISTS SONGS"):
			return
		if not self.execute("DROP TABLE IF EXISTS PLAYLISTS"):
			return
		if not self.execute("DROP TABLE IF EXISTS SONGS_PLAYLISTS"):
			return

		# Create a Songs table
		success = self.execute("""CREATE TABLE SONGS(
			id					INTEGER PRIMARY KEY AUTOINCREMENT,
			title				TEXT,
			artist				TEXT,
			album				TEXT,
			genres				TEXT,
			duration_ms			INTEGER,
			file_path			TEXT	UNIQUE,
			file_hash			TEXT	UNIQUE
		)""")

		if not success:
			return

		# Create a Playlists table
		success = self.execute("""CREATE TABLE PLAYLISTS(
			id					INTEGER PRIMARY KEY AUTOINCREMENT,
			playlist_name		TEXT,
			is_auto_playlist	INTEGER
		)""")

		if not success:
			return

		# Create a table for songs in Playlists
		success = self.execute("""CREATE TABLE SONGS_PLAYLISTS(
			song_id						INTEGER,
			playlist_id					INTEGER,
			FOREIGN KEY(song_id)		REFERENCES SONGS(id) ON DELETE CASCADE,
			FOREIGN KEY(playlist_id)	REFERENCES PLAYLISTS(id) ON DELETE CASCADE
		)""")
		# ON DELETE CASCADE will automatically delete the corresponding row in the child table
		# when the row in the parent table is deleted.

		if not success:
			return
		
		# Create a table for folders to scan music from
		success = self.execute("""CREATE TABLE FOLDERS(
			id				INTEGER PRIMARY KEY AUTOINCREMENT,
			folder_path		TEXT	UNIQUE,
			is_checked		INTEGER
		)""")

		self.commit()

	# Executes the sql query
	def execute(self, sql_string: str, params: tuple =()) -> bool:
		try:
			self.db_cursor.execute(sql_string, params)
			print("-----")
			print("SQL Query: {}".format(sql_string))
			print("Params: {}".format(params))
			print("-----\n")
		except Exception as e:
			print("-----")
			print("Failed SQL Query:{}\n".format(sql_string))
			print("Param: {}".format(params))
			print("Error: {}".format(e))
			print("-----\n")
			return False

		return True
	
	# Commit changes to database
	def commit(self) -> None:
		self.db_conn.commit()

	# ----------------------------------------------------------------
	# SQL Queries
	# ----------------------------------------------------------------

	def add_song(self, title: str, artist: str, album: str, genres: str,
			  		duration_ms: int, file_path: str, file_hash: str) -> bool:
		
		sql_query = """
			INSERT INTO SONGS (title, artist, album, genres, duration_ms, file_path, file_hash)
			VALUES (?, ?, ?, ?, ?, ?, ?)
		"""
		
		success = self.execute(sql_query, (title, artist, album, genres, duration_ms, file_path, file_hash))
		if not success:
			return False

		self.commit()
		return True
	
	def get_song(self, id: int) -> object:

		sql_query = """
			SELECT * FROM SONGS
			WHERE id=?
		"""

		self.execute(sql_query, (id,))

		song = self.db_cursor.fetchone()
		return song

	def edit_song(self, id: int, title: str, artist: str, album: str, genres: str) -> bool:

		sql_query = """
			UPDATE SONGS
			SET title=?, artist=?, album=?, genres=?
			WHERE id=?
		"""

		success = self.execute(sql_query, (title, artist, album, genres, id))

		if not success:
			return False
		
		self.commit()
		return True

	def remove_song(self, song_id) -> bool:

		sql_query = """
			DELETE FROM SONGS
			WHERE id=?
		"""

		success = self.execute(sql_query, (song_id,))

		if not success:
			return False
		
		self.commit()
		return True
	
	def remove_songs_from_folder(self, file_path: str) -> bool:

		sql_query = """
			DELETE FROM SONGS
			WHERE file_path
			LIKE ?
		"""

		success = self.execute(sql_query, (file_path + '%',))

		if not success:
			return False
		
		self.commit()
		return True
	
	def check_song_exists(self, file_hash: str) -> bool:
		sql_query = """
			SELECT * FROM SONGS
			WHERE file_hash=?
		"""

		self.execute(sql_query, (file_hash,))

		song = self.db_cursor.fetchone()

		return song != None

	def add_playlist(self, playlist_name: str, is_auto_playlist: int) -> bool:
		
		sql_query = """
			INSERT INTO PLAYLISTS (playlist_name, is_auto_playlist)
			VALUES (?, ?)
		"""

		success = self.execute(sql_query, (playlist_name, is_auto_playlist))

		if not success:
			return False

		self.commit()
		return True

	def update_playlist(self, playlist_id: int, playlist_name: str) -> bool:
		sql_query = """
			UPDATE PLAYLISTS
			SET playlist_name=?
			WHERE id=?
			"""

		success = self.execute(sql_query, (playlist_name, playlist_id))

		if not success:
			return False

		self.commit()
		return True

	def delete_playlist(self, playlist_id: int) -> bool:
		sql_query = """
			DELETE FROM PLAYLISTS
			WHERE id=?
			"""

		success = self.execute(sql_query, (playlist_id,))

		if not success:
			return False

		self.commit()
		return True
	
	# Add song to playlist
	def add_song_to_playlist(self, song_id: int, playlist_id: int) -> bool:

		sql_query = """
			INSERT INTO SONGS_PLAYLISTS (song_id, playlist_id)
			VALUES (?, ?)
			"""

		success = self.execute(sql_query, (song_id, playlist_id))

		if not success:
			return False

		self.commit()
		return True

	# Remove song from playlist
	def remove_song_from_playlist(self, song_id: int, playlist_id: int) -> bool:

		sql_query = """
			DELETE FROM SONGS_PLAYLISTS
			WHERE song_id=?
			AND playlist_id=?
			"""

		success = self.execute(sql_query, (song_id, playlist_id))

		if not success:
			return False

		self.commit()
		return True
	
	def get_all_playlists(self) -> list:
		sql_query = """
			SELECT * FROM PLAYLISTS
		"""

		self.execute(sql_query)

		all_playlists = self.db_cursor.fetchall()

		return all_playlists

	def get_songs_in_playlist(self, playlist_name: str) -> list:

		sql_query = """
			SELECT id FROM PLAYLISTS
			WHERE playlist_name=?
		"""
		
		self.execute(sql_query, (playlist_name,))

		database_results = self.db_cursor.fetchone()
		songs = []
		
		if database_results != None:
			playlist_id = database_results["id"]
			
			sql_query = """
				SELECT song_id FROM SONGS_PLAYLISTS
				WHERE playlist_id=?
			"""

			self.execute(sql_query, (playlist_id,))

			results = self.db_cursor.fetchall()

			for result in results:
				song_id = result["song_id"]
				
				sql_query = """
					SELECT * FROM SONGS
					WHERE id=?
				"""

				self.execute(sql_query, (song_id,))

				song = self.db_cursor.fetchone()
				songs.append(song)
				print(f"Song: {song["title"]}\n{song["artist"]}\n{song["genres"]}")

		return songs

	def get_all_songs(self) -> list:

		sql_query = """
			SELECT * FROM SONGS
		"""

		self.execute(sql_query)

		all_songs = self.db_cursor.fetchall()

		return all_songs
	
	def is_song_in_playlist(self, song_id: int, playlist_id: int) -> bool:

		sql_query = """
			SELECT 1 FROM SONGS_PLAYLISTS
			WHERE song_id=?
			AND playlist_id=?
		"""

		self.execute(sql_query, (song_id, playlist_id))
		
		return self.db_cursor.fetchone() is not None
	
	def add_folder(self, folder_path: str, is_checked: int) -> bool:

		sql_query = """
			INSERT INTO FOLDERS (folder_path, is_checked)
			VALUES (?, ?)
		"""

		success = self.execute(sql_query, (folder_path, is_checked))

		if not success:
			return False
		
		self.commit()
		return True

	def modify_check_folder(self, folder_path: str, is_checked: int) -> bool:

		sql_query = """
			UPDATE FOLDERS
			SET is_checked=?
			WHERE folder_path=?
			"""

		success = self.execute(sql_query, (is_checked, folder_path))

		if not success:
			return False

		self.commit()
		return True
	
	def get_folders(self) -> list:

		sql_query = """
			SELECT * FROM FOLDERS
		"""

		self.execute(sql_query)

		all_folders = self.db_cursor.fetchall()

		return all_folders
	
	def check_folder_exists(self, folder_path: str) -> bool:

		sql_query = """
			SELECT * FROM FOLDERS
			WHERE folder_path=?
		"""

		self.execute(sql_query, (folder_path,))

		folder = self.db_cursor.fetchone()

		return folder != None
	
	def remove_folder(self, folder_path: str) -> bool:

		sql_query = """
			DELETE FROM FOLDERS
			WHERE folder_path=?
			"""

		success = self.execute(sql_query, (folder_path,))

		if not success:
			return False

		self.commit()
		return True