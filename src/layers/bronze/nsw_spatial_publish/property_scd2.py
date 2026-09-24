# SCD Type 2 modeling of NSW Spatial Services' Property layer.
#
# Keyed by `addressstringoid`, not `propid` -- discovered via a real dev
# run, not assumed upfront. `propid` identifies the parent Property, which
# can contain multiple addressable units (e.g. a unit block); every unit
# shares the same `propid`/`gurasid`/`principaladdresssiteoid` but has its
# own `address` and `addressstringoid`. A real run against `propid` would
# have silently merged unrelated units' history into one "entity" --
# confirmed the mismatch (486 distinct `propid` among 500 rows) before
# building this, then confirmed `addressstringoid` is unique across all 500
# rows with zero NULLs.
from pyspark import pipelines as dp

dp.create_streaming_table(name="property_scd2")
dp.create_auto_cdc_from_snapshot_flow(
    target="property_scd2",
    source="bronze_nsw_spatial.property_raw",
    keys=["addressstringoid"],
    stored_as_scd_type=2,
)
