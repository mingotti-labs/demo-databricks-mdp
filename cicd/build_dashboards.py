"""Writes the generated dashboard and Genie agent files from their builders in src/common.

Usage: uv run python cicd/build_dashboards.py [--check]
--check writes nothing and fails when a committed file differs from its builder (as apply_edition.py --check does).
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from common import inflation_dashboard, market_climate_dashboard, market_climate_genie  # noqa: E402

GENERATED = {
    ROOT / "src" / "dashboards" / "market_climate.lvdash.json": market_climate_dashboard.build,
    ROOT / "src" / "dashboards" / "inflation_deflation.lvdash.json": inflation_dashboard.build,
    ROOT / "resources" / "genie" / "market_climate.genie.yml": market_climate_genie.build,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale = []
    for path, build in GENERATED.items():
        content = build()
        if path.exists() and path.read_text(encoding="utf-8").replace("\r\n", "\n") == content:
            continue
        stale.append(path)
        if not args.check:
            path.write_text(content, encoding="utf-8", newline="\n")
            print("wrote", path.relative_to(ROOT))
    if args.check and stale:
        print("out of date, run cicd/build_dashboards.py:", *[str(p.relative_to(ROOT)) for p in stale], sep="\n  ")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
