# Databricks notebook source
# Generates one batch of synthetic clickstream event files into the
# bronze_clickstream landing volume, for Phase 3b's Auto Loader pattern. Each
# run adds a new batch and never overwrites a prior one -- unlike
# seed_neon_ecommerce.py's truncate-and-reseed, this is meant to accumulate
# across runs so Auto Loader has an ongoing stream of files to discover.
# Batches after the first include extra fields the first batch doesn't have,
# to exercise Auto Loader's schema evolution with real data.
import json
import random
import uuid

from faker import Faker

dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")

LANDING_PATH = f"/Volumes/{catalog}/bronze_clickstream/s3_clickstream_raw/web_events/landing"
NUM_EVENTS_PER_BATCH = 200
EVENT_TYPES = ["page_view", "click", "add_to_cart", "purchase", "search"]

# COMMAND ----------

try:
    existing_files = [f for f in dbutils.fs.ls(LANDING_PATH) if f.name.endswith(".json")]
except Exception:
    existing_files = []

batch_number = len(existing_files)
include_new_fields = batch_number > 0  # first batch (0) stays on the base schema

Faker.seed(42 + batch_number)
random.seed(42 + batch_number)
fake = Faker()

# COMMAND ----------

events = []
for _ in range(NUM_EVENTS_PER_BATCH):
    event = {
        "event_id": str(uuid.uuid4()),
        "session_id": str(uuid.uuid4()),
        "user_id": random.randint(1, 500),
        "event_type": random.choice(EVENT_TYPES),
        "page_url": fake.uri_path(),
        "timestamp": fake.date_time_between(start_date="-30d", end_date="now").isoformat(),
    }
    if include_new_fields:
        event["device_type"] = random.choice(["desktop", "mobile", "tablet"])
        event["referrer_url"] = fake.uri()
    events.append(event)

# COMMAND ----------

batch_file = f"{LANDING_PATH}/batch_{batch_number:03d}.json"
content = "\n".join(json.dumps(e) for e in events)
dbutils.fs.put(batch_file, content, overwrite=True)

dbutils.notebook.exit(
    f"batch={batch_number} events={len(events)} "
    f"new_fields={'yes' if include_new_fields else 'no'} file={batch_file}"
)
