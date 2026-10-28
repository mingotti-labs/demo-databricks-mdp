# Databricks notebook source
# Copies the CSV files a glob names (committed in the repo, deployed with the
# bundle) into a Unity Catalog volume, one folder per file:
# /Volumes/<catalog>/<schema>/<volume>/<name>/landing/<name>.csv, overwriting the
# previous copy. The repo is the master; the volume always matches `main`.
import glob
import os
import shutil

dbutils.widgets.text("source_glob", "")
dbutils.widgets.text("catalog", "")
dbutils.widgets.text("schema", "")
dbutils.widgets.text("volume", "")
source_glob = dbutils.widgets.get("source_glob")
volume_root = "/Volumes/{}/{}/{}".format(
    dbutils.widgets.get("catalog"), dbutils.widgets.get("schema"), dbutils.widgets.get("volume")
)

# COMMAND ----------

files = sorted(glob.glob(source_glob))
assert files, f"no files match {source_glob}"
for path in files:
    name = os.path.splitext(os.path.basename(path))[0]
    destination = f"{volume_root}/{name}/landing"
    os.makedirs(destination, exist_ok=True)
    shutil.copyfile(path, f"{destination}/{name}.csv")
    print(f"{path} -> {destination}/{name}.csv")

dbutils.notebook.exit(f"Copied {len(files)} files to {volume_root}")
