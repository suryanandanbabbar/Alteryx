"""Pandas/NumPy expression emitter.

Transforms a Lark parse tree (from the Alteryx expression grammar)
into Python/pandas code strings.
"""

from __future__ import annotations

import re
from lark import Transformer, Token, Tree


# Direct function mappings: Alteryx name (lowered) → pandas / numpy / python method
_DIRECT_MAP: dict[str, str] = {
    "trim": ".str.strip()",
    "trimleft": ".str.lstrip()",
    "ltrim": ".str.lstrip()",
    "trimright": ".str.rstrip()",
    "rtrim": ".str.rstrip()",
    "length": ".str.len()",
    "len": ".str.len()",
    "upper": ".str.upper()",
    "uppercase": ".str.upper()",
    "lower": ".str.lower()",
    "lowercase": ".str.lower()",
    "titlecase": ".str.title()",
    "abs": ".abs()",
}


class PandasEmitter(Transformer):
    """Transforms Alteryx expression parse trees into pandas code strings.

    The emitter produces code strings that reference a DataFrame variable
    (default: 'df'). Field references like [Revenue] become df["Revenue"].
    """

    def __init__(self, df_var: str = "df"):
        super().__init__()
        self.df_var = df_var
        self._imports: set[str] = set()
        self._diagnostics: list[str] = []

    @property
    def imports(self) -> set[str]:
        """Return import statements needed by the emitted code."""
        return self._imports.copy()

    @property
    def diagnostics(self) -> list[str]:
        """Return warning messages encountered during emission."""
        return self._diagnostics.copy()

    # ── Atoms ──────────────────────────────────────────────────

    def start(self, children):
        return children[0]

    def number(self, children):
        token = children[0]
        return str(token)

    def string(self, children):
        token = str(children[0])
        # Normalize to double quotes
        inner = token[1:-1]
        # Escape any unescaped double quotes inside
        inner_escaped = inner.replace('"', '\\"')
        return f'"{inner_escaped}"'

    def boolean(self, children):
        token = str(children[0]).lower()
        return "True" if token == "true" else "False"

    def null_func(self, children):
        return "None"

    def field_ref(self, children):
        token = str(children[0])
        name = token[1:-1]  # strip [ ]
        return f'{self.df_var}["{name}"]'

    def bare_field(self, children):
        token = str(children[0])
        return f'{self.df_var}["{token}"]'

    def row_ref(self, children):
        token = str(children[0])
        m = re.match(r"\[Row-(\d+):(.+)\]", token)
        if m:
            offset = m.group(1)
            field = m.group(2)
            return f'{self.df_var}["{field}"].shift({offset})'
        m_plus = re.match(r"\[Row\+(\d+):(.+)\]", token)
        if m_plus:
            offset = m_plus.group(1)
            field = m_plus.group(2)
            return f'{self.df_var}["{field}"].shift(-{offset})'
        return f'{self.df_var}["{token.strip("[]")}"]'

    # ── Arithmetic ─────────────────────────────────────────────

    def add(self, children):
        return f"({children[0]} + {children[1]})"

    def sub(self, children):
        return f"({children[0]} - {children[1]})"

    def mul(self, children):
        return f"({children[0]} * {children[1]})"

    def div(self, children):
        return f"({children[0]} / {children[1]})"

    def mod(self, children):
        return f"({children[0]} % {children[1]})"

    def neg(self, children):
        return f"(-{children[0]})"

    # ── Comparison ─────────────────────────────────────────────

    def eq(self, children):
        # children: [left, EQ_token, right]
        return f"({children[0]} == {children[2]})"

    def neq(self, children):
        # children: [left, NEQ_token, right]
        return f"({children[0]} != {children[2]})"

    def gt(self, children):
        # children: [left, GT_token, right]
        return f"({children[0]} > {children[2]})"

    def gte(self, children):
        # children: [left, GTE_token, right]
        return f"({children[0]} >= {children[2]})"

    def lt(self, children):
        # children: [left, LT_token, right]
        return f"({children[0]} < {children[2]})"

    def lte(self, children):
        # children: [left, LTE_token, right]
        return f"({children[0]} <= {children[2]})"

    def in_expr(self, children):
        value = children[0]
        args = []
        for c in children[1:]:
            if isinstance(c, Token):
                continue
            if isinstance(c, list):
                args = c
            else:
                args.append(c)
        values_str = ", ".join(str(a) for a in args)
        return f"({value}.isin([{values_str}]))"

    # ── Logical ────────────────────────────────────────────────

    def or_expr(self, children):
        # children: [left, OR_token, right]
        return f"({children[0]} | {children[2]})"

    def and_expr(self, children):
        # children: [left, AND_token, right]
        return f"({children[0]} & {children[2]})"

    def not_expr(self, children):
        # children: [NOT_token, expr]
        return f"(~{children[1]})"

    # ── IF / ELSEIF / ELSE / ENDIF ────────────────────────────

    def if_expr(self, children):
        self._imports.add("import numpy as np")
        parts = [c for c in children if not isinstance(c, Token)]
        cond = parts[0]
        then_val = parts[1]
        elseifs = [p for p in parts[2:-1] if isinstance(p, tuple)]
        else_val = parts[-1]

        if elseifs:
            result = else_val
            for ei_cond, ei_val in reversed(elseifs):
                result = f"np.where({ei_cond}, {ei_val}, {result})"
            return f"np.where({cond}, {then_val}, {result})"
        else:
            return f"np.where({cond}, {then_val}, {else_val})"

    def elseif_clause(self, children):
        parts = [c for c in children if not isinstance(c, Token)]
        return (parts[0], parts[1])

    # ── Function calls ─────────────────────────────────────────

    def func_call(self, children):
        func_name = str(children[0])
        args = children[1] if len(children) > 1 else []
        if not isinstance(args, list):
            args = []

        func_lower = func_name.lower()

        # Null / condition handling
        if func_lower == "isnull":
            return f"{args[0]}.isna()"
        if func_lower == "isnotnull":
            return f"{args[0]}.notna()"
        if func_lower == "isempty":
            return f'({args[0]} == "")'
        if func_lower == "iif":
            self._imports.add("import numpy as np")
            if len(args) >= 3:
                return f"np.where({args[0]}, {args[1]}, {args[2]})"
            elif len(args) >= 2:
                return f"np.where({args[0]}, {args[1]}, None)"
            return "None"
        if func_lower in ("coalesce", "ifnull"):
            if len(args) >= 2:
                return f"{args[0]}.fillna({args[1]})"
            return args[0] if args else "None"
        if func_lower == "null":
            return "None"

        # String functions
        if func_lower in ("trim", "strip"):
            if len(args) >= 2:
                return f"{args[0]}.str.strip({args[1]})"
            elif args:
                return f"{args[0]}.str.strip()"
            return '""'
        if func_lower in ("ltrim", "trimleft"):
            if len(args) >= 2:
                return f"{args[0]}.str.lstrip({args[1]})"
            elif args:
                return f"{args[0]}.str.lstrip()"
            return '""'
        if func_lower in ("rtrim", "trimright"):
            if len(args) >= 2:
                return f"{args[0]}.str.rstrip({args[1]})"
            elif args:
                return f"{args[0]}.str.rstrip()"
            return '""'
        if func_lower in ("upper", "uppercase"):
            return f"{args[0]}.str.upper()"
        if func_lower in ("lower", "lowercase"):
            return f"{args[0]}.str.lower()"
        if func_lower in ("titlecase", "totitle"):
            return f"{args[0]}.str.title()"
        if func_lower in ("length", "len"):
            return f"{args[0]}.str.len()"
        if func_lower in ("padleft",):
            pad_char = args[2] if len(args) > 2 else repr(" ")
            return f"{args[0]}.str.pad({args[1]}, side='left', fillchar={pad_char})"
        if func_lower in ("padright",):
            pad_char = args[2] if len(args) > 2 else repr(" ")
            return f"{args[0]}.str.pad({args[1]}, side='right', fillchar={pad_char})"
        if func_lower == "contains":
            return f"{args[0]}.str.contains({args[1]}, na=False)"
        if func_lower == "startswith":
            return f"{args[0]}.str.startswith({args[1]})"
        if func_lower == "endswith":
            return f"{args[0]}.str.endswith({args[1]})"
        if func_lower == "left":
            return f"{args[0]}.str[:int({args[1]})]"
        if func_lower == "right":
            return f"{args[0]}.str[-int({args[1]}):]"
        if func_lower in ("substring", "mid"):
            if len(args) >= 3:
                return f"{args[0]}.str[int({args[1]})-1:int({args[1]})-1+int({args[2]})]"
            elif len(args) >= 2:
                return f"{args[0]}.str[int({args[1]})-1:]"
            return args[0] if args else '""'
        if func_lower in ("replace", "replacefirst"):
            if len(args) >= 3:
                return f"{args[0]}.str.replace({args[1]}, {args[2]}, regex=False)"
            return args[0] if args else '""'
        if func_lower == "findstring":
            if len(args) >= 2:
                return f"{args[0]}.str.find({args[1]})"
            return "-1"
        if func_lower == "tostring":
            return f"{args[0]}.astype(str)"
        if func_lower == "tonumber":
            return f"pd.to_numeric({args[0]}, errors='coerce')"
        if func_lower == "tointeger":
            return f"pd.to_numeric({args[0]}, errors='coerce').astype('Int64')"

        # Math functions
        if func_lower == "round":
            if len(args) >= 2:
                return f"{args[0]}.round(int({args[1]}))"
            return f"{args[0]}.round()"
        if func_lower == "ceil":
            self._imports.add("import numpy as np")
            return f"np.ceil({args[0]})"
        if func_lower == "floor":
            self._imports.add("import numpy as np")
            return f"np.floor({args[0]})"
        if func_lower == "pow":
            if len(args) >= 2:
                return f"({args[0]} ** {args[1]})"
            return args[0] if args else "0"
        if func_lower == "log":
            self._imports.add("import numpy as np")
            return f"np.log({args[0]})"
        if func_lower == "log10":
            self._imports.add("import numpy as np")
            return f"np.log10({args[0]})"
        if func_lower == "sqrt":
            self._imports.add("import numpy as np")
            return f"np.sqrt({args[0]})"
        if func_lower == "min":
            self._imports.add("import numpy as np")
            if len(args) >= 2:
                return f"np.minimum({args[0]}, {args[1]})"
            return args[0] if args else "0"
        if func_lower == "max":
            self._imports.add("import numpy as np")
            if len(args) >= 2:
                return f"np.maximum({args[0]}, {args[1]})"
            return args[0] if args else "0"

        # Date / Time functions
        if func_lower == "datetimetoday":
            self._imports.add("import pandas as pd")
            return "pd.Timestamp.today().normalize()"
        if func_lower == "datetimenow":
            self._imports.add("import pandas as pd")
            return "pd.Timestamp.now()"
        if func_lower == "datetimediff":
            self._imports.add("import pandas as pd")
            unit = str(args[2]).strip("\"'").lower() if len(args) > 2 else "days"
            d1 = f"pd.to_datetime({args[0]})"
            d2 = f"pd.to_datetime({args[1]})"
            if unit in ("days", "d", "day"):
                return f"({d1} - {d2}).dt.days"
            elif unit in ("hours", "h", "hour"):
                return f"({d1} - {d2}).dt.total_seconds() / 3600"
            elif unit in ("minutes", "m", "minute"):
                return f"({d1} - {d2}).dt.total_seconds() / 60"
            elif unit in ("seconds", "s", "second"):
                return f"({d1} - {d2}).dt.total_seconds()"
            elif unit in ("years", "y", "year"):
                return f"({d1} - {d2}).dt.days / 365.25"
            elif unit in ("months", "month"):
                return f"({d1} - {d2}).dt.days / 30.4375"
            else:
                return f"({d1} - {d2}).dt.days"
        if func_lower == "datetimeadd":
            self._imports.add("import pandas as pd")
            amt = args[1] if len(args) > 1 else "0"
            unit = str(args[2]).strip("\"'").lower() if len(args) > 2 else "days"
            unit_map = {"days": "D", "hours": "h", "minutes": "m", "seconds": "s"}
            pd_unit = unit_map.get(unit, "D")
            return f"(pd.to_datetime({args[0]}) + pd.to_timedelta({amt}, unit='{pd_unit}'))"
        if func_lower == "datetimeformat":
            self._imports.add("import pandas as pd")
            fmt = args[1] if len(args) > 1 else "'%Y-%m-%d'"
            return f"pd.to_datetime({args[0]}).dt.strftime({fmt})"

        # Direct map check
        if func_lower in _DIRECT_MAP:
            return f"{args[0]}{_DIRECT_MAP[func_lower]}"

        # Unknown function — safe valid Python fallback without inline comments that break syntax inside expressions
        args_str = ", ".join(str(a) for a in args)
        self._diagnostics.append(f"Unsupported Alteryx function: {func_name}({args_str})")
        return "None"

    def func_args(self, children):
        return list(children)


# ── Convenience function ─────────────────────────────────────────────


def emit_pandas(expression: str, df_var: str = "df") -> tuple[str, set[str]]:
    """Parse and emit a pandas expression from an Alteryx expression string.

    Args:
        expression: Alteryx expression string.
        df_var: DataFrame variable name to use.

    Returns:
        Tuple of (pandas_code_string, set_of_import_statements).

    Raises:
        lark.exceptions.LarkError: If the expression cannot be parsed.
    """
    from awa.expressions.parser import parse_expression

    tree = parse_expression(expression)
    emitter = PandasEmitter(df_var=df_var)
    result = emitter.transform(tree)
    return str(result), emitter.imports
