from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

@dataclass
class Node:
	parent: str
	name: str

@dataclass
class Comparison:
    field: str
    operator: str
    value: str


@dataclass
class And:
    left: Expression
    right: Expression


@dataclass
class Or:
    left: Expression
    right: Expression

Expression: TypeAlias = Comparison | And | Or