"""Small local symbol-context demo for Week 5.

An editor-grade implementation would ask an LSP server for definitions and
references. This dependency-free version demonstrates the same context-saving
principle for Python: expose just the requested symbol, not the entire file.
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path


def find_symbol_source(path: Path, symbol: str) -> str:
    """Return the source span for a top-level Python class or function."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    lines = source.splitlines(keepends=True)
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol:
            end = getattr(node, "end_lineno", node.lineno)
            return "".join(lines[node.lineno - 1:end])
    raise ValueError(f"Top-level symbol {symbol!r} was not found in {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Show focused Python symbol context")
    parser.add_argument("path", type=Path, help="Python source file")
    parser.add_argument("symbol", help="Top-level class or function name")
    args = parser.parse_args()
    try:
        print(find_symbol_source(args.path, args.symbol), end="")
    except (OSError, SyntaxError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    main()
