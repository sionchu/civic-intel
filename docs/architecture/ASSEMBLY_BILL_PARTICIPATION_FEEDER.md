# National Assembly bill participation feeder

## Purpose

This feeder enumerates every official member-proposed bill row in one National Assembly term
so representative and co-proposer participation can be resolved from exact member codes rather
than names.

It is an L3 collection lane. It does not scrape bill-detail HTML, infer proposal-reason text,
score legislators or publish faction/alliance claims.

## Official contract

Reviewed on 2026-08-31:

```text
catalog: https://www.data.go.kr/data/15125946/openapi.do
endpoint: https://open.assembly.go.kr/portal/openapi/nzmimeepazxkubdpn
required scope: AGE
pagination: pIndex, pSize, list_total_count
provider row key: BILL_ID
representative codes: RST_MONA_CD
co-proposer codes: PUBL_MONA_CD
```

The catalog records free access, 이용허락범위 제한 없음, development auto-approval,
operational review approval and provider-controlled traffic allowance.

## Bounded universe

One run covers exactly:

```text
assembly_age:{AGE}
```

Bill ID, number, name, committee, result or proposer filters are prohibited for L3. Review
staging may still project one known `MONA_CD` from the complete scan, but the persistent source
universe itself is never name-filtered.

## Coverage contract

The source does not expose a trusted provider-side page echo. Complete coverage therefore
requires all of:

- page 1 start;
- stable `list_total_count`;
- expected page count within the configured safety maximum;
- exact expected row count on every page;
- every row `AGE` matching the scope;
- unique `BILL_ID` across the term;
- no repeated page fingerprint;
- both proposer-code fields present and parseable on every row;
- final unique bill count equal to `list_total_count`.

Any ambiguity fails closed. A previously committed page remains resumable, but the incomplete
run is `PARTIAL` and cannot support exact term counts.

## Persistent observation

```text
feeder: national_assembly_bill_participation
scope_key: assembly_age:{AGE}
provider_record_key: BILL_ID
semantic_scope: legislative_bill_participation
```

The normalized record retains only:

- bill ID, number and title;
- Assembly term and proposal date;
- committee name/code and raw processing result;
- exact representative/co-proposer member-code sets;
- a credential-scrubbed official detail link;
- explicit code-linked participation semantics.

Display-name proposer strings and `PROPOSER` summary text are deliberately omitted because they
are unnecessary for exact member-code participation. Request credentials are absent from Source
URLs, snapshots, observations, checkpoints and run errors. SourceSnapshot remains metadata-only.

## Identity and publication boundary

One bill can contain multiple people, so this observation is a multi-person legislative event,
not a Person roster row. Identity hints retain participant `MONA_CD` and role only.

The feeder does not:

- AUTO_CREATE a Person;
- match by display name;
- merge Persons;
- publish a Claim directly;
- classify processing results as legislative performance;
- infer faction, alliance, influence or responsibility from co-proposal.

Canonical publication still requires the existing Person/Claim/ClaimEvidence/Source/SourcePolicy
path and an accepted exact member identity.

## Run and resume

Each page is fetched and parsed before one transaction persists/reuses Source and SourceSnapshot,
inserts or reuses immutable FeederObservations, and advances the checkpoint. Persistence failure
leaves the checkpoint at the last committed page.

```text
same BILL_ID + same normalized hash -> unchanged
same BILL_ID + changed normalized hash -> new immutable observation
```

Resume requires the same term, page size and source contract as the saved checkpoint.

## Operational entrypoint

After migrating the configured database and injecting `ASSEMBLY_API_KEY` only at runtime:

```bash
civic-stage-legislative --age 22 --page-size 1000 --enumerate-bills \
  --database-url sqlite:///civic-intel.db
```

Resume:

```bash
civic-stage-legislative --age 22 --page-size 1000 --resume \
  --database-url sqlite:///civic-intel.db
```

These commands collect metadata into the batch foundation. They do not scrape detail pages or
publish profile content.
