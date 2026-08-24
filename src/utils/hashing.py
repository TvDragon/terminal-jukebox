from hashlib import sha256

def calculate_hash(input_str: str, is_file_path: bool = False) -> str:
	hasher = sha256()

	if not is_file_path:
		with open(input_str, "rb") as file:
			while chunk := file.read(8192):
				hasher.update(chunk)
	else:
		hasher.update(input_str.encode("utf-8"))

	return hasher.hexdigest()