# Civic Intel Portrait Pilot v0

Status: implementation complete; local production artifact verified; awaiting commit/CI closure

## Objective and boundary

Add the smallest possible portrait presentation slice for one already resolved canonical
Person. The asset is local and static, is shown only on `/people/[id]`, and is not a feeder,
identity authority, API field, database record, directory field or staging deployment.

Excluded: Assembly portrait ingestion, Commons search, bulk enumeration, face recognition,
embeddings, generated portraits, name-only binding, directory images, new API/DTO/schema/table,
Railway changes, staging deployment and remote runtime image fetches.

## Baseline and source gate

- Repository SSOT is the actual remote head `4e7477d242ef2035c576e3085d4eb73956c06ceb` in the
  isolated `codex/change-discovery-plan` worktree. The attachment's baseline
  `86af562b8ae09526d7c35b62a9d7ee006e333cc0` is not present in this repository; no history was
  rewritten and the dirty root checkout remains untouched.
- Pilot Person: `44745d09-398c-46ce-bc38-81f0f606c1d7`, canonical name 안철수, existing Assembly
  provider anchor `MONA_CD=YOG1280B`. The read-only staging dossier is `RESOLVED` and publishes
  the Assembly Base Profile; the official Assembly page independently matches name, party,
  district, committee and reelection. Contact fields are not retained.
- The selected file is [Ahn Cheol-soo March 2023 (cropped).jpg](https://commons.wikimedia.org/wiki/Image%3AAhn_Cheol-soo_March_2023_%28cropped%29.jpg).
  MediaWiki imageinfo returned creator 이데일리TV, CC BY 3.0, JPEG, 400×534, 38,558 bytes,
  SHA-1 `46f16ce27199a761bb472cb0f68a763a3afa16db` and revision timestamp
  `2024-12-22T05:13:12Z`. The [CC BY 3.0 license](https://creativecommons.org/licenses/by/3.0/)
  is recorded at file level. The [official Assembly profile](https://www.assembly.go.kr/members/22nd/AHNCHEOLSOO/)
  supplies the independent identity context.
- The exact original URL, file title, page, creator, license, attribution, revision, hash,
  dimensions and Assembly crosswalk are stored in the presentation-only manifest. A changed
  revision, deletion, withdrawal or rights change fails closed to the initials fallback pending
  new review.

## Implementation contract

- `apps/web/public/portraits/manifest.json` contains exactly one `ELIGIBLE` reviewed record and
  `apps/web/public/portraits/44745d09-398c-46ce-bc38-81f0f606c1d7.jpg` is the exact downloaded
  local copy. The [MediaWiki Imageinfo contract](https://www.mediawiki.org/wiki/API:Imageinfo)
  is used only for source reconnaissance and file-level verification.
- The server Person page performs an exact resolved `Person.id` lookup into the manifest. It
  does not compare names or make the manifest an identity authority. Unmatched, unresolved or
  withdrawn records retain the existing CI stamp; `/people` retains initials rows.
- The detail view uses a native local `<img>` with the reviewed 400:534 aspect ratio, visible
  creator/source/license links and an expandable hash/revision audit. It does not show the
  remote original as the runtime image and does not expose raw normalized observations or
  contact fields.
- `check-portrait-assets.mjs` checks manifest fields, local containment, file existence, bytes
  and SHA-1. No dependency or persistence change is introduced.

## Verification record

Required evidence is kept separate: source API/file review, local asset integrity, static tests,
production standalone artifact, local browser smoke and CI Verify. Staging/Railway is not part of
this plan.

- MediaWiki imageinfo matched the reviewed contract exactly; the downloaded local file is 38,558
  bytes with SHA-1 `46f16ce27199a761bb472cb0f68a763a3afa16db`. The image was opened and visually
  inspected as a 400×534 vertical portrait.
- `npm test --prefix apps/web`: portrait integrity plus 11 UI tests passed. Web lint, typecheck,
  full Python pytest (`355 passed, 1 skipped`), Ruff, mypy (`60 source files`) and Golden quality
  passed. The only pytest output was the repository's existing dependency deprecation warnings.
- The worktree Next build first hit a Windows `EBUSY` lock on an existing empty `.next/standalone`
  directory. An exact private temp mirror with the same source, lockfile and offline-installed
  dependencies built successfully; standalone asset preparation and `check:standalone` passed.
  The lock was an environment runner issue, not a compile or type error.
- The standalone artifact was run against a disposable copy of the 299-row SQLite fixture. The
  copy contained the pilot Person UUID and reviewed Assembly profile values only for QA; the
  repository/staging database was not changed. Chrome CDP measured the requested exact viewports:
  `1280×900` and `390×844`.
- At both viewports, Home and People had no horizontal overflow, content rendered, skip-link
  focus was visible and no framework overlay appeared. People showed 299 rows, initials in all
  directory rows, no directory images, and facet options `3/299/5/5`. `박지원` returned 2 rows;
  a no-match returned 0 rows with `검색 결과가 없습니다.`. Desktop facet results were party
  `101`, district `1`, committee `75`, reelection `60`, and party+committee `25`; reset returned
  299. Mobile search/no-match and directory layout matched.
- The pilot detail showed the local `/portraits/...jpg`, natural size 400×534, rendered ratio
  preserved, visible `사진: 이데일리TV · Wikimedia Commons · CC BY 3.0`, source/license links,
  Base Profile, Evidence trace and Sources. Raw normalized/contact text was absent. A different
  Person showed the existing CI stamp with no portrait; the unknown UUID rendered `Profile not
  found`. Desktop/mobile browser console warning/error lists were empty.
- Captured screenshots are private temp evidence outside the repository:
  `portrait-detail-desktop-1280x900.png`, `portrait-detail-mobile-390x844.png`,
  `portrait-home-desktop-1280x900.png`, `portrait-home-mobile-390x844.png` and
  `portrait-people-desktop-1280x900.png`.

## Completion gate

Close this plan only after the pilot asset passes the integrity script, web tests/lint/typecheck/
build/standalone check, the existing Python/Ruff/mypy/Golden checks, local desktop/mobile browser
smoke (including fallback, directory initials, keyboard, overflow, console and evidence trace),
`git diff --check`, commit/push and CI Verify. Do not deploy staging as part of this milestone.
