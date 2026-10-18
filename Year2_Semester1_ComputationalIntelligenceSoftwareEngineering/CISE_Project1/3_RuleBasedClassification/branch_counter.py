"""Count the branching statements in a Python source file by parsing it (ast).

This is used to VERIFY the assignment constraint (at most n branching statements,
n = number of input attributes used by the classifier). It counts, over the WHOLE file:
  * every `if` / `elif`     (an `elif` is parsed as an `If` nested in the `else` branch,
                             so each `elif` counts as one statement;
                             a plain `else` is NOT counted - it is only the tail of an `if`)
  * every conditional expression  `a if cond else b`
  * every `match` statement case
  * every `if` filter inside a comprehension
It also reports the attributes read from the record (`record["name"]`).
Counting the whole file prevents hiding branches in helper functions.
"""

import ast
from pathlib import Path


def count_branching_statements(source: str) -> int:
    """Number of if/elif, conditional expressions, match cases and comprehension filters."""
    count = 0
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.If, ast.IfExp)):
            count += 1
        elif isinstance(node, ast.match_case):
            count += 1
        elif isinstance(node, ast.comprehension):
            count += len(node.ifs)
    return count


def attributes_used(source: str, known_attributes: list[str]) -> set[str]:
    """Names of input attributes accessed in the source as string constants (record["age"])."""
    constants = {n.value for n in ast.walk(ast.parse(source))
                 if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    return constants & set(known_attributes)


def count_rules(source: str) -> int:
    """Number of rules = number of `return "<label>"` statements (decision paths).

    Only informative; the assignment constraint is about branching statements, not rules.
    """
    return sum(isinstance(n, ast.Return) and isinstance(n.value, ast.Constant)
               and isinstance(n.value.value, str) for n in ast.walk(ast.parse(source)))


def check_file(path: Path, known_attributes: list[str]) -> dict:
    """Return branch count, attributes used, allowed limit and compliance flag."""
    source = Path(path).read_text(encoding="utf-8")
    used = attributes_used(source, known_attributes)
    n_branches = count_branching_statements(source)
    return {
        "attributes_used": sorted(used),
        "n_attributes_used": len(used),
        "allowed_branches": len(used),
        "branching_statements": n_branches,
        "return_statements_(rules)": count_rules(source),
        "compliant": n_branches <= len(used),
    }
