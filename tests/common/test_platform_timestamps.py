"""No run-time stamping on full snapshots in sources moved to the corrected
platform timestamps (openspec correct-platform-timestamps)."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MIGRATED = ["acnc", "ungm", "iso", "geonames", "nsw_spatial", "airroi"]

def checked_files():
    for source in MIGRATED:
        yield from (ROOT / f"src/layers/bronze/{source}_publish").glob("*.py")
        yield from (ROOT / f"src/layers/silver/landing/{source}").glob("*.py")


@pytest.mark.parametrize("path", list(checked_files()), ids=lambda p: p.name)
def test_no_current_timestamp_outside_stamping_helpers(path):
    assert "current_timestamp" not in path.read_text(), path.name
