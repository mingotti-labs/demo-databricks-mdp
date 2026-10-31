"""P2: real encoding of the MIC CSV and the 8 rows whose operating MIC is not an operating row."""
import csv
import io

import requests

URL = "https://www.iso20022.org/sites/default/files/ISO10383_MIC/ISO10383_MIC.csv"
response = requests.get(URL, timeout=60)
print("content-type", response.headers.get("content-type"))
raw = response.content
print("bytes", len(raw), "has bom", raw[:3] == b"\xef\xbb\xbf")
for enc in ("utf-8", "cp1252"):
    try:
        raw.decode(enc)
        print(enc, "decodes")
    except UnicodeDecodeError as error:
        print(enc, "fails", error)
text = raw.decode("utf-8", errors="replace")
print("non-ascii sample", sorted({c for c in text if ord(c) > 127})[:20])
rows = list(csv.DictReader(io.StringIO(text)))
operating = {r["MIC"] for r in rows if r["OPRT/SGMT"] == "OPRT"}
for r in rows:
    if r["OPERATING MIC"] not in operating:
        print(r["MIC"], r["OPERATING MIC"], r["OPRT/SGMT"], r["STATUS"], r["MARKET NAME-INSTITUTION DESCRIPTION"])
