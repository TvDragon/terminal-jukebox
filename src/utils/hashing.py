from hashlib import sha256

def calculate_string_hash(input_str: str) -> str:
	hasher = sha256()

	hasher.update(input_str.encode("utf-8"))

	return hasher.hexdigest()

def calculate_acoustic_fingerprint_hash(fingerprint: bytes) -> str:
	hasher = sha256()

	hasher.update(fingerprint)

	return hasher.hexdigest()