# Silver Normalised spec logic with no Spark dependency: loading a
# normalised spec, the cross-reference rules docs/normalised-spec/schema.json
# cannot express, the rdm_proposed_match_key rule (N8) and the drift check.
# Shared by the generic pipeline, the tag step, verification and the tests.
import re
import unicodedata

import yaml

VALIDITY_COLUMNS = ("scd_valid_from_timestamp", "scd_valid_to_timestamp", "is_current")
PLATFORM_COLUMNS = (
    *VALIDITY_COLUMNS,
    "source_name",
    "source_file_name",
    "ingested_timestamp",
    "transformed_timestamp",
)


class SpecError(ValueError):
    """A normalised spec breaks one or more cross-reference rules."""


def load_spec(path: str) -> dict:
    """Read a normalised spec and fail on any cross-reference problem."""
    with open(path, encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    problems = check(spec)
    if problems:
        raise SpecError(f"{path}:\n" + "\n".join(problems))
    return spec


def match_key(value: str | None) -> str | None:
    """N8: strip accents, collapse inner whitespace, trim, uppercase."""
    if value is None:
        return None
    decomposed = unicodedata.normalize("NFKD", value)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(stripped.split()).upper()


def landing_table(ref: str) -> str:
    """Table name of a `silver_landing_{source}.{table}` reference."""
    return ref.split(".", 1)[1]


def bridge_attribute(name: str, bridge: dict) -> str:
    """Element column of a bridge: its name without the `{parent}_` prefix."""
    return name.removeprefix(bridge["parent"] + "_")


def members(spec: dict) -> dict[str, list[tuple[str, str, str]]]:
    """Member columns per extracted entity, as (kind, entity, column).

    For a bridge member, `column` is the bridge's element column.
    """
    result: dict[str, list[tuple[str, str, str]]] = {}
    for name, base in spec["base_entities"].items():
        for column, target in base.get("extracted", {}).items():
            result.setdefault(target, []).append(("base", name, column))
    for name, bridge in spec.get("bridge_entities", {}).items():
        if "extracted" in bridge:
            result.setdefault(bridge["extracted"], []).append(
                ("bridge", name, bridge_attribute(name, bridge))
            )
    return result


def parent_column(base: dict, parent: str) -> str:
    """The one column of a base entity mapped to extracted entity `parent`."""
    (column,) = [c for c, t in base.get("extracted", {}).items() if t == parent]
    return column


def base_output_columns(base: dict) -> list[str]:
    """Natural key, kept columns, then foreign keys not already listed."""
    columns = list(base["natural_key"]) + list(base["columns"])
    return columns + [c for c in base.get("extracted", {}) if c not in columns]


def tables(spec: dict) -> dict[str, str | None]:
    """Every table the pipeline builds, mapped to its mdp.entity_kind.

    value_lineage and quarantine tables are not an entity kind (None).
    """
    result: dict[str, str | None] = {name: "base" for name in spec["base_entities"]}
    result.update(
        {
            f"{t['entity']}_quarantine": None
            for t in spec.get("dependency_tolerance", [])
        }
    )
    result.update({name: "bridge" for name in spec.get("bridge_entities", {})})
    result.update({name: "extracted" for name in spec.get("extracted_entities", {})})
    result["value_lineage"] = None
    return result


def like_to_regex(pattern: str) -> re.Pattern:
    """SQL LIKE pattern (`%`, `_`) as a case-insensitive full-match regex."""
    parts = (
        "." if ch == "_" else ".*" if ch == "%" else re.escape(ch) for ch in pattern
    )
    return re.compile("".join(parts), re.IGNORECASE)


def check(spec: dict) -> list[str]:
    """Cross-reference problems in a schema-valid spec; empty when none."""
    problems: list[str] = []
    source = spec["source_system"]
    bases = spec["base_entities"]
    bridges = spec.get("bridge_entities", {})
    extracted = spec.get("extracted_entities", {})
    tables = [*bases.items(), *bridges.items()]

    for name, entity in tables:
        if not entity["from"].startswith(f"silver_landing_{source}."):
            problems.append(
                f"{name}: from {entity['from']} is outside silver_landing_{source}"
            )

    names = [*bases, *bridges, *extracted]
    for name in sorted({n for n in names if names.count(n) > 1}):
        problems.append(f"{name}: entity name used more than once")
    for name in names:
        if name == "value_lineage" or name.endswith("_quarantine"):
            problems.append(f"{name}: reserved table name")

    for name, bridge in bridges.items():
        parent = bases.get(bridge["parent"])
        if parent is None:
            problems.append(f"{name}: parent {bridge['parent']} is not a base entity")
        elif bridge["from"] != parent["from"]:
            problems.append(f"{name}: from differs from its parent's from")

    found = members(spec)
    for target in sorted(set(found) - set(extracted)):
        problems.append(f"{target}: mapped as an extracted entity but not declared")
    for name in sorted(set(extracted) - set(found)):
        problems.append(f"{name}: extracted entity has no member column")

    problems += _hierarchy_problems(extracted)
    problems += _resolution_problems(bases, extracted, found)

    for tolerance in spec.get("dependency_tolerance", []):
        base = bases.get(tolerance["entity"])
        if base is None:
            problems.append(f"tolerance: {tolerance['entity']} is not a base entity")
            continue
        used = base_output_columns(base)
        for key in ("determinant", "dependent"):
            if tolerance[key] not in used:
                problems.append(
                    f"tolerance on {tolerance['entity']}: {tolerance[key]} is not used by it"
                )

    ignored = set(spec["ignored_columns"])
    for name, base in bases.items():
        table = landing_table(base["from"])
        for column in base_output_columns(base):
            if f"{table}.{column}" in ignored:
                problems.append(f"{table}.{column}: both used and ignored")
    return problems


def _hierarchy_problems(extracted: dict) -> list[str]:
    problems = []
    for name, entity in extracted.items():
        seen, current = {name}, entity.get("parent")
        while current is not None:
            if current not in extracted:
                problems.append(f"{name}: parent {current} is not an extracted entity")
                break
            if current in seen:
                problems.append(f"{name}: parent chain has a cycle")
                break
            seen.add(current)
            current = extracted[current].get("parent")
    return problems


def _resolution_problems(bases: dict, extracted: dict, found: dict) -> list[str]:
    problems = []
    for name, entity in extracted.items():
        parent = entity.get("parent")
        if not parent and not entity.get("attributes"):
            continue
        for kind, owner, _ in found.get(name, []):
            if kind == "bridge":
                problems.append(
                    f"{name}: has a parent or attributes, so it cannot have bridge members"
                )
                continue
            if parent:
                mapped = [
                    c
                    for c, t in bases[owner].get("extracted", {}).items()
                    if t == parent
                ]
                if len(mapped) != 1:
                    problems.append(
                        f"{name}: {owner} needs exactly one column mapped to parent {parent}, has {len(mapped)}"
                    )
    return problems


def used_columns(spec: dict, table: str, landing_columns: list[str]) -> set[str]:
    """Landing columns of one table that the spec reads."""
    used: set[str] = set()
    for base in spec["base_entities"].values():
        if landing_table(base["from"]) != table:
            continue
        used.update(base_output_columns(base))
        for target in set(base.get("extracted", {}).values()):
            used.update(spec["extracted_entities"][target].get("attributes", []))
    for bridge in spec.get("bridge_entities", {}).values():
        if landing_table(bridge["from"]) != table:
            continue
        if "explode" in bridge:
            used.add(bridge["explode"]["column"])
        else:
            pattern = like_to_regex(bridge["unpivot"]["columns_like"])
            used.update(c for c in landing_columns if pattern.fullmatch(c))
    return used


def drift(spec: dict, landing: dict[str, list[str]]) -> list[str]:
    """Drift problems between the spec and live Landing columns per table."""
    problems = []
    ignored = {tuple(c.split(".", 1)) for c in spec["ignored_columns"]}
    for table, columns in landing.items():
        used = used_columns(spec, table, columns)
        for column in columns:
            if (
                column not in used
                and column not in PLATFORM_COLUMNS
                and (table, column) not in ignored
            ):
                problems.append(f"{table}.{column}: neither used nor ignored")
        for column in sorted(used - set(columns)):
            problems.append(
                f"{table}.{column}: used by the spec but missing in Landing"
            )
    return problems
