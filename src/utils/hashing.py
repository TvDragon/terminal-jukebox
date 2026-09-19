from hashlib import sha256

def calculate_string_hash(input_str: str) -> str:
	hasher = sha256()

	hasher.update(input_str.encode("utf-8"))

	return hasher.hexdigest()

def calculate_file_hash(path: str) -> str:
	hasher = sha256()

	with open(path, "rb") as file:
		while chunk := file.read(8192):
			hasher.update(chunk)

	return hasher.hexdigest()