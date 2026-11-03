"""Pipeline source files must not run Spark actions while the graph is built.

`.first()`, `.collect()` or `.toPandas()` inside a decorated function runs before the
update has loaded upstream tables, so on a new environment it sees them empty (abs-cpi
loaded 0 rows in prd). Use a window or a join, which are evaluated at run time.
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIPELINE_DIRS = ["bronze", "silver/landing", "silver/domain"]
ACTIONS = {"first", "collect", "toPandas"}


def eager_actions(source: str) -> list[int]:
    """Line numbers of calls to Spark actions in `source`."""
    return [
        node.lineno
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in ACTIONS
    ]


def test_detects_the_abs_bug():
    source = 'raw = spark.read.table("t")\nlatest = raw.agg(max("c")).first()[0]\n'
    assert eager_actions(source) == [2]


def test_pipeline_sources_have_no_eager_actions():
    offenders = {}
    for directory in PIPELINE_DIRS:
        for path in (ROOT / "src" / "layers" / directory).rglob("*.py"):
            if lines := eager_actions(path.read_text(encoding="utf-8")):
                offenders[path.relative_to(ROOT).as_posix()] = lines
    assert not offenders, offenders
