# Dividend portfolio probes

Throwaway probes for the OpenSpec change `dividend-portfolio-probes`: each
script answers one question about a source before the story's source changes
are designed. Results are in that change's `design.md` and in
`references/docs/registers/probes.md`. Not part of the bundle (`references/**`
is excluded from sync).

| Script | Question | Packages |
|---|---|---|
| `p1_hosts.py` | Can serverless reach each source's host? | `requests` |
| `p2_table_count.py` | How many tables does the metastore hold? | none |
| `p3_wikipedia.py` | Can the S&P 500 page be parsed? | `requests lxml` |
| `p4_fmp.py` | What does the FMP free plan give? (at most 15 calls) | `requests` |
| `p4b_fmp_calendar.py` | Is the FMP calendar free without dates? (1 call) | `requests` |
| `p5_sec.py` | Do SEC company facts cover the figures? | `requests` |
| `p6_yahoo.py` | Does `yfinance` fetch the whole index? | `yfinance requests lxml` |
| `p6b_yahoo_calendar.py` | Does `yfinance` give pay dates? | `yfinance requests lxml` |

Run one at a time (Free Edition), from this folder:

```
uv run python run.py p1_hosts --profile <PROFILE> --deps requests
```

`run.py` uploads this folder to `/Workspace/Users/<you>/poc/dividend-portfolio/`,
submits the script as a one-time serverless job and prints its output. FMP
probes read the key from the `fmp` secret scope and never print it.
