# Scheduled acquisition (acquisition-only)

`civic-acquire` (`workers/scheduled_acquisition.py`) runs existing L3 source workers on a cadence.
It only refreshes observations, runs and checkpoints. It never passes `--materialize`,
`--publish-*`, `--resolve-review-item` or `--commit`, and it does not call `civic-sync` (which
materializes People). Person materialization, Claim publication and public output stay separate,
reviewed operations. A scheduled run alone does not promote any feeder to `L4 PRODUCTION_SYNC`:
freshness, reconciliation and monitoring evidence are still required.

## Jobs

| Job | Cadence | Worker / flags | Credential |
|---|---|---|---|
| `assembly-roster` | daily | `workers.assembly_roster --enumerate` | `ASSEMBLY_API_KEY` |
| `assembly-bills` | daily | `workers.legislative_activity --age $CIVIC_ASSEMBLY_AGE (22) --enumerate-bills` | `ASSEMBLY_API_KEY` |
| `alio-executives` | weekly | `workers.public_institutions` | none |
| `mois-organization-codes` | weekly | `workers.mois_organization_codes` | `MOIS_ORG_CODE_API_KEY` |
| `opendart-listed-executives` | monthly | `workers.corporate_talent --dataset EXECUTIVE_STATUS --enumerate --listed-only` for `$CIVIC_DART_BUSINESS_YEAR` / `$CIVIC_DART_REPORT_CODE` (explicit; no default) | `DART_API_KEY` |

Not scheduled, and why:

- NEC candidates/winners: election-scoped; run once per election, not on a cadence.
- Gwanbo personnel notices: every live window tried so far (7 days, 31 days, three years) returns
  `SUCCESS` with zero notices, so a scheduled run would only repeat an empty response. Investigate
  the route/parameters before scheduling it.
- Assembly asset disclosure (부동산·재산): `L0 RESEARCHED; BLOCKED` in
  `FEEDER_SOURCE_COVERAGE.md` (Gazette origin, revision/key and route contract unresolved).
- News, public statements (발언), roll-call votes: no SourcePolicy-approved lane exists. News and
  curated compilations are discovery-only; statements need primary-source verification first.
- Political orientation (정치성향): never collected as a fact. Per the North Star it can only be a
  later Derived Intelligence view over official votes/sponsorship with its own approved method.

Statuses per job: `SUCCESS`, `WORKER_PARTIAL`/`WORKER_FAILED`, `FAILED`, `TIMEOUT`,
`BLOCKED_CREDENTIAL`, `BLOCKED_CONFIG`, `PLANNED` (dry run). Exit code: `1` on any failure, `3`
when only blocked jobs remain, `75` when another run holds the lock, else `0`. Interrupted
enumerations are not auto-resumed; rerun one job with `--only <job> --resume`.

Receipts: one JSON line per invocation in `$CIVIC_ACQUISITION_RECEIPTS_DIR`
(default `~/.civic-intel/acquisition-receipts/YYYY-MM.jsonl`), outside Git and the canonical DB.
Credentials are redacted; they are read from the environment by the workers and never put in argv.

## Commands

```bash
civic-acquire --list
civic-acquire --cadence daily --dry-run
civic-acquire --cadence daily
civic-acquire --only alio-executives --resume
```

## Mac (target host)

1. Private env file `~/Developer/civic-intel-serve/acquisition.env` with `chmod 600`, containing
   `DATABASE_URL`, `CIVIC_HTTP_USER_AGENT`, the API keys and `CIVIC_DART_*`. Never commit it.
2. Replace `__DEPLOY_DIR__` and `__LOG_DIR__` in `deploy/launchd/kr.civicintel.acquisition.*.plist`,
   copy them to `~/Library/LaunchAgents/`, then
   `launchctl bootstrap gui/$UID ~/Library/LaunchAgents/kr.civicintel.acquisition.daily.plist`
   (and weekly/monthly). Times: daily 04:17, weekly Sunday 05:07, monthly day 2 05:37 (local).
3. First run manually: `bash deploy/launchd/run-acquisition.sh daily`, then inspect receipts.

Run against the canonical DB only after a backup and an explicit owner decision; the first
scheduled run on a new host should target a staging copy.

## Windows (test only)

Use a disposable SQLite DB, never the canonical DB:

```powershell
$env:DATABASE_URL = 'sqlite:///C:/Users/<you>/ci-acq-test/acq.db'
$env:CIVIC_ACQUISITION_RECEIPTS_DIR = 'C:\Users\<you>\ci-acq-test\receipts'
python -m alembic upgrade head
python -m workers.scheduled_acquisition --cadence daily
```

The keyless job (`alio-executives`) runs without credentials; keyed jobs report
`BLOCKED_CREDENTIAL` until the operator sets the variables in that session. A Task Scheduler
entry may call the same command for a cadence test.
