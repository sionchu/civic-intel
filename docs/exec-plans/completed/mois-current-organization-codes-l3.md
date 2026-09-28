# MOIS Current Organization-Code L3

Status: COMPLETE — merged-master persistent L3 run verified on the Mac staging/data server.

## Objective

Persist the complete current `stop_selt=0` MOIS Standard Organization Code universe as immutable
Source/Snapshot/FeederObservation data without creating canonical Organizations, Claims, Gukgam
bindings, or cross-source identity merges.

## Verified live contract — 2026-09-26

Credentialed read-only audit of `StanOrgCd2/getStanOrgCdList2`:

- total current rows: `133,907`;
- page size `1000` is honored;
- expected pages: `134`;
- final page rows: `907`;
- distinct `org_cd`: `133,907`;
- duplicate `org_cd`: `0`;
- full parsed manifest SHA-256: `b7a860b57355e28e7a7f18ca0acce2b1f5a93116d0e5598adf0e8efaef052a91`;
- `stop_selt=0`: all `133,907` rows;
- every row has at least one of `full_nm` / `low_nm`;
- current provider code namespace is seven uppercase alphanumeric characters;
- observed code shapes include numeric codes, `B/C/D/P` prefixes, and mixed forms such as
  `1Z00189`;
- lifecycle dates outside `crt_de` are valid `YYYYMMDD`/empty across the audited universe; `crt_de`
  has three legacy/anomalous values (`1988. 1.`, `19660900`, `19901131`). They are preserved as raw
  `created_date_text` with no normalized date, so Civic Intel never invents a day or repairs provider data.

The live audit made 134 bounded API requests and performed no database writes.

## Source-policy boundary

`apis.data.go.kr` is a host-level SourcePolicy namespace in Civic Intel. NEC and MOIS therefore
share the existing policy UUID `12000000-0000-0000-0000-000000000001`. The code definition is
consolidated into one reviewed host-level policy while NEC and MOIS retain separate endpoint/source
contracts and separate credential variables.

Before the first persistent MOIS run, the existing staging SourcePolicy row must be reconciled only
after exact precondition checks. The policy UUID, domain, permissions, existing Source rows and
source identities must not change.

## L3 contract

Feeder: `mois_standard_organization_codes`

Scope: `current:stop_selt=0`

Source contract: `mois_standard_organization_code_v1`

Provider record key: exact `org_cd`

Checkpoint stores only bounded coverage metadata:

- page size / expected pages / total count;
- committed provider count;
- deterministic manifest SHA-256;
- page fingerprints.

It deliberately does not store a 133k-entry provider-key/hash map in checkpoint JSON.

Resume is allowed only before the first successful full enumeration. The worker reconstructs the
committed manifest from existing observations and verifies its digest before continuing. After a
successful full enumeration, a later failed refresh must restart from page 1 rather than infer a
version manifest from mixed historical observations.

## Materialization boundary

This slice creates no canonical Organization rows. `org_cd` is an official provider Organization
key, not a Civic Intel Organization UUID and not authority for automatic Gukgam binding.

Permitted sequence after L3:

`MOIS observation -> reviewed Organization proposal -> exact reviewed binding -> explicit Claim`

No fuzzy/name-only/embedding automatic merge is authorized.

## Verification gates

- focused connector + worker tests;
- full Ruff / mypy / pytest / Golden Set;
- GitHub Verify;
- merged-master staging preflight;
- fresh pg_dump backup;
- host-policy exact reconciliation;
- persistent L3 run;
- post-count/checkpoint/source fingerprint verification.

## Stop condition

Stop after one complete persistent current-universe run is verified against that run's provider
total. Do not create Organizations or Gukgam Claims in the same operation.

## Disposable live L3 proof — 2026-09-27

Before any staging write, the merged-candidate implementation was exercised against the real
MOIS API with a disposable SQLite database migrated through schema 0008:

- full live enumeration: 134/134 pages;
- current observations committed: 133,907;
- unique provider record keys: 133,907;
- final checkpoint cursor: 134;
- final checkpoint total / seen count: 133,907 / 133,907;
- final SourceRun status: SUCCESS;
- canonical Person rows created: 0;
- canonical Organization rows created: 0;
- Claim rows created: 0.

This proved the persistent L3 worker path without mutating staging at the 2026-09-27 audit snapshot.

## Persistent L3 closure — 2026-09-28

The merged-master worker at `107c0f0f75e9d120954c4b846b31adbdc955a248` completed the
current `stop_selt=0` universe on the Mac staging/data PostgreSQL server at schema `0008`:

- provider total / committed observations: `133,930 / 133,930`;
- pages: `134 / 134`;
- checkpoint cursor: `134`;
- checkpoint total / seen count: `133,930 / 133,930`;
- latest SourceRun: `SUCCESS`;
- unique provider record keys: `133,930`;
- People remained `9,120`;
- Organizations remained `347` during the MOIS collection slice;
- Claims/ClaimEvidence remained `14,397 / 14,397`.

The earlier `133,907` value above remains valid as the 2026-09-26 audit snapshot. The provider
current-universe total changed by `23` before the persistent run; Civic Intel preserved the live
provider total rather than hard-coding the earlier audit count.

A post-run pg_dump was created and later backup/restore verification reproduced the database
counts on disposable PostgreSQL. The L3 milestone is therefore complete.

The next permitted boundary is a separate review-only Organization proposal from persisted MOIS
observations. Provider `org_code` remains source identity only and cannot authorize automatic
canonical Organization creation or Gukgam Claim publication.
