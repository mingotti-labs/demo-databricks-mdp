"""P1: shape of the ISO 10383 MIC CSV: key uniqueness, blanks, date formats."""
import csv
import io
import sys
from collections import Counter

import requests

URL = "https://www.iso20022.org/sites/default/files/ISO10383_MIC/ISO10383_MIC.csv"
response = requests.get(URL, timeout=60)
response.raise_for_status()
rows = list(csv.DictReader(io.StringIO(response.text)))
print("rows", len(rows), "columns", list(rows[0]))
print("encoding", response.encoding, "starts with", repr(response.text[:20]))
keys = Counter(r["MIC"] for r in rows)
print("distinct MIC", len(keys), "duplicates", [k for k, v in keys.items() if v > 1][:5])
print("OPRT/SGMT", Counter(r["OPRT/SGMT"] for r in rows))
print("STATUS", Counter(r["STATUS"] for r in rows))
for col in ["CREATION DATE", "LAST UPDATE DATE", "LAST VALIDATION DATE", "EXPIRY DATE"]:
    values = [r[col] for r in rows if r[col]]
    print(col, "filled", len(values), "sample", values[:3], "lengths", Counter(len(v) for v in values))
operating = {r["MIC"] for r in rows if r["OPRT/SGMT"] == "OPRT"}
orphans = [r["MIC"] for r in rows if r["OPERATING MIC"] not in operating]
print("rows whose operating MIC is not an OPRT row", len(orphans), orphans[:5])
print("OPRT rows with OPERATING MIC != MIC", sum(1 for r in rows if r["OPRT/SGMT"] == "OPRT" and r["OPERATING MIC"] != r["MIC"]))
blank_country = sum(1 for r in rows if not r["ISO COUNTRY CODE (ISO 3166)"])
print("blank country", blank_country)
sample = [r for r in rows if r["MIC"] in ("XNYS", "XASX", "XTKS", "XJPX")]
for r in sample:
    print({k: r[k] for k in ["MIC", "OPERATING MIC", "OPRT/SGMT", "MARKET NAME-INSTITUTION DESCRIPTION", "ISO COUNTRY CODE (ISO 3166)", "STATUS", "CREATION DATE", "EXPIRY DATE"]})
sys.exit(0)
