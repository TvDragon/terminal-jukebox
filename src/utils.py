from hashlib import sha256
import unicodedata

def normalise_text(text: str) -> str:
	# NFD = Normalization Form Decomposed
	# Mn = Mark, Nonspacing
	normalised_text = unicodedata.normalize("NFD", text)

	final_text = ""
	for character in normalised_text:
		category = unicodedata.category(character)
		if category != "Mn":
			final_text += character

	return final_text.lower()

def calculate_hash(input_str: str, is_file_path: bool = False) -> str:
	hasher = sha256()

	if not is_file_path:
		with open(input_str, "rb") as file:
			while chunk := file.read(8192):
				hasher.update(chunk)
	else:
		hasher.update(input_str.encode("utf-8"))

	return hasher.hexdigest()