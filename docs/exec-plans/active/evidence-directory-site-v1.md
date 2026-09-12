# Evidence Directory site v1

Status: completed — stop condition met locally on 2026-09-13.

## Objective

Turn the existing Evidence Directory v0 verification surface into a usable public site for the
canonical resolved-person roster and evidence-backed profiles. Preserve the existing API,
domain, persistence and publication gates; this plan is web-only.

## Scope

- establish the root `DESIGN.md` visual contract;
- make the public roster legible, searchable by displayed canonical name and responsive;
- make profile navigation, coverage, claims, conflicts and source provenance easier to inspect;
- keep `/admin/review` read-only and unadvertised from public navigation;
- verify desktop/mobile rendering, route navigation, console/error state and existing web tests.

This plan does not add a feeder, source, schema, migration, raw payload store, publication action,
identity merge action, OpenWatch data, asset/vote dashboard or new API endpoint.

## Baseline

Captured on 2026-09-13 before implementation:

```text
branch: master
local/origin HEAD: 400a7ee9c1e2360e6fd82e5caeb90d99ee4da6f2
tracked tree: clean
web stack: Next.js App Router / React 19 / TypeScript
existing web verification: lint, typecheck, 4 UI tests and build passed
existing API: roster, public profile/source reads and opt-in read-only review report
```

## Milestones

### A — Visual contract and shell

- [x] read governing docs and actual web implementation
- [x] establish `DESIGN.md` without external brand copying or runtime dependencies
- [x] preserve the public-only navigation boundary

### B — Evidence Directory UI

- [x] implement the responsive public shell and roster
- [x] add client-side name filtering without identity semantics
- [x] improve profile section navigation and evidence/source audit readability
- [x] preserve read-only review route behavior and payload boundaries
- [x] add deterministic UI regressions for the new public surface

### C — Verification and delivery

- [x] web lint, typecheck, tests and production build
- [x] local API + Next runtime smoke with disposable migrated Golden database
- [x] direct desktop and mobile visual inspection
- [x] console/error overlay and navigation checks
- [x] diff/clean-v0 review and coherent commit/push
- [x] update `HANDOFF.md` with actual evidence and next action

## Verification evidence

- `npm --prefix apps/web run lint`: exit 0.
- `npm --prefix apps/web run typecheck`: exit 0.
- `npm --prefix apps/web test`: 5 passed.
- `npm --prefix apps/web run build`: exit 0; `/`, `/admin/review` and `/people/[id]`
  built successfully.
- `.venv\Scripts\python.exe -m pytest`: 282 passed, 4 warnings in 92.62s.
- `.venv\Scripts\python.exe -m ruff check apps packages workers tests`: passed.
- `.venv\Scripts\python.exe -m mypy packages workers apps/api`: success for 51 source files.
- `.venv\Scripts\python.exe -m packages.verification.quality`: `passed: true`; all Golden Set
  checks passed.
- The disposable migrated Golden database served the local API while Next rendered the roster,
  resolved profile and default-unavailable review route. The in-app browser showed the 10-person
  roster, filtered `이원주` to one displayed result, followed a profile link, and showed no
  approval/merge/publication control. The default API returned 404 for `/admin/review`.
- Direct desktop inspection covered the home roster, profile and review surface. A 390x844 mobile
  emulation captured the home and profile; the document had no horizontal overflow, the profile
  layout measured 350px wide, and the source grid collapsed to one column. The captures were
  opened and inspected after the final responsive adjustment.
- `make verify` is unavailable on this Windows host because GNU Make is not installed; every
  constituent command was run directly. `git diff --check` passed before delivery, and the final
  commit/push left `HEAD == origin/master` with a clean worktree.

## Stop condition

Stop this site milestone when the public roster and profile are readable at desktop and mobile
widths, every rendered evidence item still exposes its existing status/provenance path, the
review route remains read-only and unlinked publicly, the web and repository verification gates
pass, and `HEAD == origin/master` with a clean worktree.
