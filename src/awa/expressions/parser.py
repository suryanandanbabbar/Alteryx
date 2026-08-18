"""Alteryx expression parser using Lark.

Parses Alteryx expression strings into Lark parse trees.
The grammar is target-independent; the emitter handles translation.
"""

from __future__ import annotations

from pathlib import Path

from lark import Lark, Tree


# Load grammar once at module level
_GRAMMAR_PATH = Path(__file__).parent / "grammar.lark"
_parser: Lark | None = None


def _get_parser() -> Lark:
    """Lazily initialize and return the Lark parser."""
    global _parser
    if _parser is None:
        grammar_text = _GRAMMAR_PATH.read_text(encoding="utf-8")
        _parser = Lark(
            grammar_text,
            parser="earley",
            ambiguity="resolve",
        )
    return _parser


def parse_expression(expression: str) -> Tree:
    """Parse an Alteryx expression string into a Lark parse tree.

    Args:
        expression: Alteryx expression string (e.g., '[Revenue] > 100').

    Returns:
        Lark Tree representing the parsed expression.

    Raises:
        lark.exceptions.LarkError: If the expression cannot be parsed.
    """
    parser = _get_parser()
    return parser.parse(expression)
