from hashlib import sha256

from models.model import Comparison, And, Or, Expression

import re
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

# ============================================================
# Tokenizer
# ============================================================

TOKEN_PATTERN = re.compile(
    r"""
    \s*
    (
        \(
        |
        \)
        |
        !=
        |
        !:
        |
        =
        |
        :
        |
        "(?:\\.|[^"\\])*"
        |
        '(?:\\.|[^'\\])*'
        |
        [A-Za-z_][A-Za-z0-9_]*
    )
    """,
    re.VERBOSE,
)

def normalize(value: str) -> str:
	# casefold() is more robust than lower() for case-insensitive matching.
	return value.strip().casefold()

def evaluate_comparison(comparison: Comparison, song: object) -> bool:
	search_value = normalize(comparison.value)

	if comparison.field == "title" or comparison.field == "artist" or comparison.field == "album":
		song_value = normalize(song[comparison.field])

		if comparison.operator == "=":
			return song_value == search_value
		if comparison.operator == ":":
			return search_value in song_value
		if comparison.operator == "!=":
			return song_value != search_value
		if comparison.operator == "!:":
			return search_value not in song_value

		raise ValueError(
			f"Operator {comparison.operator} not supported for genre"
		)
	elif comparison.field == "genre":
		song_genres = {
			normalize(genre)
			for genre in song["genres"].split(";")
			if genre.strip()
		}

		if comparison.operator == ":":
			for genre in song_genres:
				if search_value in genre:
					return True

			return False

		if comparison.operator == "!:":
			for genre in song_genres:
				if search_value in genre:
					return False

			return True
		
		raise ValueError(
			f"Operator {comparison.operator} not supported for genre"
		)
	else:
		raise ValueError(
			f"Field \'{comparison.field}\' is not valid"
		)


def evaluate(expression: Expression, song: object) -> bool:
	if isinstance(expression, Comparison):
		return evaluate_comparison(expression, song)

	if isinstance(expression, And):
		return (
			evaluate(expression.left, song)
			and evaluate(expression.right, song)
		)

	if isinstance(expression, Or):
		return (
			evaluate(expression.left, song)
			or evaluate(expression.right, song)
		)

	raise TypeError(
		f"Unsupported expression node: {type(expression).__name__}"
	)

class FilterParser:
	def __init__(self, tokens):
		self.tokens = tokens
		self.index = 0

	def consume(self):
		if self.index >= len(self.tokens):
			raise ValueError(
				"Unexpected end of expression. Invalid advanced filter-search."
			)
		token = self.tokens[self.index]
		self.index += 1
		return token

	def parse_comparison(self):
		field = self.consume()
		operator = self.consume()
		value = self.consume()

		return Comparison(
			field,
			operator,
			value[1:-1]
		)

	def current(self):
		if self.index >= len(self.tokens):
			return None
		return self.tokens[self.index]

	def parse_primary(self):
		if self.current() == "(":
			self.consume()

			node = self.parse_or()

			if self.consume() != ")":
				raise ValueError("Expected ')'")

			return node

		return self.parse_comparison()
	
	def parse_and(self):
		left = self.parse_primary()

		while (
			self.index < len(self.tokens)
			and self.tokens[self.index] == "AND"
		):
			self.consume()
			right = self.parse_primary()
			left = And(left, right)

		return left

	def parse_or(self):
		left = self.parse_and()

		while (
			self.index < len(self.tokens)
			and self.tokens[self.index] == "OR"
		):
			self.consume()
			right = self.parse_and()
			left = Or(left, right)

		return left

	def parse(self):
		result = self.parse_or()

		if self.index < len(self.tokens):
			raise ValueError(
				f"Unexpected token: {self.tokens[self.index]}\n"
				f"Invalid advanced filter-search."
			)

		return result

def tokenize(filter_text: str) -> list: # Rich-text editors may replace normal quotes with curly quotes.
	filter_text = (
		filter_text
		.replace("“", '"')
		.replace("”", '"')
		.replace("‘", "'")
		.replace("’", "'")
	)

	tokens: list[str] = []
	position = 0

	while position < len(filter_text):
		match = TOKEN_PATTERN.match(filter_text, position)

		if match is None:
			# Allow trailing whitespace.
			if filter_text[position:].strip() == "":
				break

			raise ValueError(
				f"Invalid filter syntax at position {position}: "
				f"{filter_text[position:position + 20]!r}"
			)

		tokens.append(match.group(1))
		position = match.end()

	return tokens

def parse_filter(filter_text: str) -> Expression:
	tokens = tokenize(filter_text)
	parser = FilterParser(tokens)
	return parser.parse()

def search_songs(songs: list[object], filter_text: str) -> list:
	expression = parse_filter(filter_text)
	return [ song for song in songs if evaluate(expression, song) ]
