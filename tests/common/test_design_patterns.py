import re
from pathlib import Path

import pytest

from common.design_patterns import load_mapping, pattern_for

ROOT = Path(__file__).resolve().parents[2]
MAPPING = load_mapping(ROOT / "src/common/design_patterns.yml")
REGISTER = (ROOT / "references/docs/registers/design-patterns.md").read_text()
REGISTER_IDS = set(re.findall(r"^### (\w+)$", REGISTER, re.M))
SOURCE_CODE = "\n".join(p.read_text() for p in (ROOT / "src/layers").rglob("*.py"))


def all_ids():
    for source, entry in MAPPING.items():
        for key, pid in {**entry["schemas"], **entry.get("tables", {})}.items():
            yield source, key, pid


@pytest.mark.parametrize("source,key,pid", list(all_ids()))
def test_pattern_id_is_in_register(source, key, pid):
    assert pid in REGISTER_IDS, f"{source}: {key} maps to unknown pattern {pid}"


@pytest.mark.parametrize("source", MAPPING)
def test_override_tables_exist_in_source(source):
    for key in MAPPING[source].get("tables", {}):
        assert key.split(".")[1] in SOURCE_CODE, f"{key} not found in src/layers"


def test_override_beats_schema_default():
    acnc = MAPPING["acnc"]
    assert pattern_for(acnc, "bronze_acnc", "charity_register_raw") == "bronze_custom_ckan_python"
    assert (
        pattern_for(acnc, "bronze_acnc", "charity_register_quarantine")
        == "bronze_quarantine_null_key_python"
    )
