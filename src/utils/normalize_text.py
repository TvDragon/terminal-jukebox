import unicodedata

def normalize_text(text: str) -> str:
	# NFD = Normalization Form Decomposed
	# Mn = Mark, Nonspacing
	normalized_text = unicodedata.normalize("NFD", text)

	final_text = ""
	for character in normalized_text:
		category = unicodedata.category(character)
		if category != "Mn":
			final_text += character

	return final_text.lower()