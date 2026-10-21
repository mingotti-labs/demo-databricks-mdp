# Source systems

One file per upstream data source this project ingests from — what it is, how
auth/access works, real (not documented) request/response shapes where they
diverge, and known gotchas. Complements `CLAUDE.md`'s "Sources" section (the
canonical build history/decision record); these files are the standing
reference for the source itself, kept current independent of which OpenSpec
change originally built it.

API-based sources:
- [airroi.md](airroi.md) — short-term rental market intelligence, paid API
- [acnc.md](acnc.md) — ACNC charity register, CKAN REST API
- [nsw_spatial.md](nsw_spatial.md) — NSW property layer, ArcGIS FeatureServer REST API
- [ungm.md](ungm.md) — UN Global Marketplace UNSPSC classification tree, REST API

Non-API sources:
- [neon.md](neon.md) — Neon Postgres, Lakeflow Connect query-based ingestion
- [clickstream.md](clickstream.md) — synthetic file-drop, Auto Loader
