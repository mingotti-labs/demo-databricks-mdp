## 1. Setup

- [ ] 1.1 Create `references/poc/dividend-portfolio/` with a README (what each
      probe asks, how to upload and run it); each probe's script is added in
      its task below; `ruff check` passes on the folder
- [ ] 1.2 Upload the folder to `/Workspace/Users/<user>/poc/dividend-portfolio/`
      before each run; verify with `databricks workspace list`
- [ ] 1.3 User supplies the SEC `User-Agent` string (app name and contact email)

## 2. Probes (one serverless run at a time, design.md D1 and D2)

- [ ] 2.1 P1 reaching the hosts; record each host's status in design.md
- [ ] 2.2 P2 metastore table count; record per-catalog counts and the headroom
- [ ] 2.3 P3 Wikipedia page; record row count, columns, CIK and date checks
- [ ] 2.4 P4 FMP free plan; record each endpoint's result and the calls used
      (at most 15), with no key in any output
- [ ] 2.5 P5 SEC company facts; record the concept coverage table and the
      `frames` result
- [ ] 2.6 P6 Yahoo; record timings, missing tickers, blocking, and the bulk
      dividend comparison

## 3. Record and decide

- [ ] 3.1 design.md "Probe results": one entry per probe (date, method, result
      as pass / pass with a constraint / fail / probe error)
- [ ] 3.2 design.md "Decisions from the probes": the S&P 500 list source, the
      pay-date source, the Yahoo path, and the story's table budget
- [ ] 3.3 Add a "Dividend portfolio sources" section to
      `references/docs/registers/probes.md`, one row per probe
- [ ] 3.4 If a result changes the story design, update it in
      `demo-databricks-planning` (separate PR); list any schema that becomes
      unnecessary for a later iac change
- [ ] 3.5 With the user's approval, delete the uploaded workspace folder (the
      repo copy stays); verify it no longer lists
