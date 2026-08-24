from hashlib import sha256

from models.model import Comparison, And, Or, Expression, SongInfo

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

def evaluate_comparison(comparison: Comparison, song: SongInfo) -> bool:
	search_value = normalize(comparison.value)
	field = comparison.field

	if field == "title" or field == "artist" or field == "album":
		song_value = None
		if field == "title":
			song_value = normalize(song.title)
		elif field == "artist":
			song_value = normalize(song.artist)
		elif field == "album":
			song_value = normalize(song.album)

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
			for genre in song.genres.split(";")
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


def evaluate(expression: Expression, song: SongInfo) -> bool:
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

def search_songs(songs: list[SongInfo], filter_text: str) -> list:
	expression = parse_filter(filter_text)
	return [ song for song in songs if evaluate(expression, song) ]

# ============================================================
# SQL QUERIES FOR ADVANCED SEARCH FILTER
# ============================================================

COLUMN_MAP = {
    "id": "id",
    "title": "title",
    "artist": "artist",
    "album": "album",

    "genre": "genres",
}

def escape_like(value: str) -> str:
    """
    Escape characters that have special meanings in SQL LIKE:

        %  matches any number of characters
        _  matches exactly one character
        \\ is used as the escape character
    """
    return (
        value
        .replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )

def compile_comparison(comparison: Comparison) -> tuple[str, list[str]]:
    field = comparison.field.casefold()
    operator = comparison.operator
    value = normalize(comparison.value)

    if field not in COLUMN_MAP:
        raise ValueError(
            f"Field {comparison.field!r} is not valid"
        )

    column = COLUMN_MAP[field]

    # title, artist and album
    if field in {"title", "artist", "album"}:
        if operator == "=":
            return (
                f"LOWER({column}) = ?",
                [value],
            )

        if operator == "!=":
            return (
                f"LOWER({column}) != ?",
                [value],
            )

        if operator == ":":
            escaped_value = escape_like(value)

            return (
                f"LOWER({column}) LIKE ? ESCAPE '\\'",
                [f"%{escaped_value}%"],
            )

        if operator == "!:":
            escaped_value = escape_like(value)

            return (
                f"LOWER({column}) NOT LIKE ? ESCAPE '\\'",
                [f"%{escaped_value}%"],
            )

        raise ValueError(
            f"Operator {operator!r} is not supported "
            f"for field {field!r}"
        )

    # genre in the filter maps to the genres database column.
    if field == "genre":
        if operator == ":":
            escaped_value = escape_like(value)

            return (
                "LOWER(genres) LIKE ? ESCAPE '\\'",
                [f"%{escaped_value}%"],
            )

        if operator == "!:":
            escaped_value = escape_like(value)

            return (
                "LOWER(genres) NOT LIKE ? ESCAPE '\\'",
                [f"%{escaped_value}%"],
            )

        raise ValueError(
            f"Operator {operator!r} is not supported "
            "for genre"
        )

    raise ValueError(
        f"Unsupported field: {field!r}"
    )

def compile_expression(expression: Expression) -> tuple[str, list[str]]:
    if isinstance(expression, Comparison):
        return compile_comparison(expression)

    if isinstance(expression, And):
        left_sql, left_parameters = compile_expression(
            expression.left
        )

        right_sql, right_parameters = compile_expression(
            expression.right
        )

        return (
            f"({left_sql} AND {right_sql})",
            left_parameters + right_parameters,
        )

    if isinstance(expression, Or):
        left_sql, left_parameters = compile_expression(
            expression.left
        )

        right_sql, right_parameters = compile_expression(
            expression.right
        )

        return (
            f"({left_sql} OR {right_sql})",
            left_parameters + right_parameters,
        )

    raise TypeError(
        f"Unsupported expression node: "
        f"{type(expression).__name__}"
    )

def build_music_query(filter_text: str) -> tuple[str, list[str]]:
    expression = parse_filter(filter_text)

    where_sql, parameters = compile_expression(expression)

    sql = (
        "SELECT *\n"
        "FROM SONGS\n"
        f"WHERE {where_sql}"
    )

    return sql, parameters
