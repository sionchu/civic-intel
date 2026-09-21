# Portrait Source Gate v0

Status: SOURCE_GATE_COMPLETE — NO IMAGE INGESTION

## Objective

Define the smallest rights-and-identity gate for adding reviewed Person portraits to Civic Intel.
This milestone is research/documentation only. It does not download image bytes, bind a portrait to
a Person, change a public read model, alter SourcePolicy, add persistence, or change Railway.

The public UI keeps the existing initials fallback until a later Portrait Pilot proves one exact
file can be used with reviewable identity, rights, attribution and version provenance.

## Baseline

- Repository baseline: `f877a99bfd41ebbc363a89fb5062931f6c3493b8`.
- Visual System v2 is `DEPLOYED_STAGING — PASS`.
- `/people` contains 299 current resolved People and uses canonical `Person.id` links.
- `apps/web/app/components/roster-grid.tsx` renders neutral initials; `Person` has no portrait field.
- No portrait/media table, image dependency, object-storage contract, image SourcePolicy or public
  portrait API exists.
- This source gate does not authorize creating any of those abstractions.

## Governing invariants

- Identity is canonical first. A filename, display name, Commons category, search result, visual
  similarity or face recognition cannot bind a file to a `Person`.
- Same-name People must remain separately reviewable. The two current canonical `박지원` records
  are the concrete regression case for why name-only image binding is prohibited.
- Technical accessibility is not reuse permission. The exact work must have a reviewable license
  or permission path suitable for the intended display, crop/resize and commercial context.
- Portrait metadata must retain exact source, creator, license, attribution and version evidence.
- A removed, replaced or relicensed upstream file must not silently change the bytes Civic Intel
  displays or the evidence for those bytes.
- No AI-generated portrait, first-search-result image, automated face matching or inferred
  likeness is permitted.

## Source A — official National Assembly member portrait

Reviewed example:

- canonical Civic Intel Person: `1bd253ae-3de7-42de-81e5-b450c1fb8e8b` (`박지원`)
- official member page: `https://www.assembly.go.kr/members/22nd/PARKJIEWON/`
- official provider identity on that page: `monaCd=8BF5855P`
- observed portrait asset:
  `/static/portal/img/openassm/new/d56ba73af8fc481bbad0165c9ed6fbe2.png`

The page provides a strong source-specific identity anchor because the member route and linked
portal URLs carry the reviewed Assembly `monaCd`. The opaque image filename is not itself a Person
identifier or a declared version contract.

The Assembly copyright policy states that works for which the National Assembly Secretariat owns
all economic rights are freely reusable when opened with the KOGL Type 1 mark, with source
attribution required. It also instructs users to consult the Assembly before using material that
has no KOGL mark.

The inspected member-profile HTML exposed the portrait as a CSS background image but did not expose
an explicit work-level KOGL Type 1 label attached to that portrait. A generic site/footer public-
Nuri affordance is not treated as a portrait-specific grant.

Decision: `NEEDS_RIGHTS_CONFIRMATION`.

Do not download, cache, crop, republish or hotlink the direct Assembly portrait until the exact work
is tied to an applicable KOGL mark or a separate rights confirmation.

References:

- `https://www.assembly.go.kr/members/22nd/PARKJIEWON/`
- `https://assembly.go.kr/portal/bbs/B0000051/view.do?cl1Cd=&edate=&nttId=3869667&pageIndex=1&pageUnit=10&sdate=&searchCnd=1&searchDtGbn=c0&searchWrd=`

## Source B — Wikimedia Commons file imported from the Assembly portrait

Reviewed file:

- Commons title: `File:박지원 의원.png`
- source declared by Commons: the official Assembly `PARKJIEWON` page
- Commons description: official portrait
- current file size: 700×1,011 PNG
- Commons-declared license: KOGL Type 1
- upload/current file date shown by Commons: 2026-08-19

The Commons page provides useful file-level metadata, but the license assertion ultimately points
back to the Assembly work. In this review, the source member page did not independently expose a
portrait-specific KOGL mark, and no separate trusted Commons license-review marker was observed for
this file.

Decision: `NEEDS_RIGHTS_REVIEW`.

The Commons license template alone is not enough for this specific candidate until the source-work
license chain is corroborated. This conservative result does not say the Commons declaration is
wrong; it says Civic Intel does not yet have the evidence required for publication.

Reference:

- `https://commons.wikimedia.org/wiki/File:%EB%B0%95%EC%A7%80%EC%9B%90_%EC%9D%98%EC%9B%90.png`

## Source C — Wikimedia Commons file with reviewed external free-license history

Reviewed candidate:

- canonical Civic Intel Person: `44745d09-398c-46ce-bc38-81f0f606c1d7` (`안철수`)
- Commons title: `File:Ahn Cheol-soo portrait.jpg`
- source: Flickr, transferred through English Wikipedia to Commons
- creator: Jinho Jung
- license: CC BY-SA 2.0 Generic
- Commons review record: on 2018-11-04, a Commons reviewer confirmed the Flickr file was available
  under the stated license on that date
- current dimensions: 814×1,066 JPEG
- current Commons checksum shown in structured data:
  `81d68d85995dee4993dbd6d173b3603c01453099` (SHA-1)
- Commons structured data depicts `Ahn Cheol-soo`

CC BY-SA permits reuse and adaptation, including commercial reuse, subject to attribution,
license notice/link, indication of changes and ShareAlike requirements for adapted versions.
Cropping or another derivative presentation must therefore retain the required credit/license and
be reviewed for the applicable ShareAlike obligation.

Decision: `ELIGIBLE_CANDIDATE` for a later manually reviewed pilot only.

This does not bind the file automatically. The final pilot must explicitly confirm that the
canonical Person and the Commons subject are the same person using public identity evidence; it
must not use facial recognition or name-only matching.

Reference:

- `https://commons.wikimedia.org/wiki/File:Ahn_Cheol-soo_portrait.jpg`

## Wikimedia reuse and version contract

Commons is a candidate-media repository, not a blanket rights oracle. Its reuse guidance says each
file may have different attribution and license requirements and that reusers should verify the
copyright status and file-specific license themselves. The original creator, not merely the
uploader, is normally the attribution target.

For files selected from Commons, a future reviewed manifest should pin the exact file revision.
MediaWiki `prop=imageinfo` can provide the current/upload-history `timestamp`, canonical file URL,
size, `sha1`, MIME type and `extmetadata`. The API response also identifies the file page/title.
These values are suitable provenance inputs for checking whether the selected upstream file changed.

Commons can delete files for copyright violations, missing legal information and other policy
reasons. Therefore a future Civic Intel copy must retain the reviewed license/source evidence and
version hash and should periodically re-check the file page for material rights changes or
withdrawal signals. A later re-check must never replace reviewed bytes silently.

References:

- `https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia/en`
- `https://www.mediawiki.org/wiki/API:Imageinfo/en`
- `https://commons.wikimedia.org/wiki/Commons:Deletion_policy/en`

## Identity gate

A portrait candidate may advance only when all of the following are true:

1. The target is one existing `RESOLVED` canonical `Person`.
2. The image source contains an identity anchor stronger than a matching display name.
3. For Assembly-origin files, a reviewed provider identifier such as `monaCd` must reconcile to
   the existing Assembly observation/link for that Person.
4. For Commons-origin files, file description/structured data may support manual review but cannot
   alone authorize an automatic canonical binding.
5. Any same-name ambiguity fails closed to human review.
6. Face recognition, embedding similarity and inferred likeness are prohibited as identity gates.

A portrait is presentation metadata. It cannot create a Person, merge People, resolve an identity
review item, create a factual Claim, or change epistemic/publication status.

## Rights gate

Before image bytes may be stored or shown, record all applicable fields:

- source kind and source page URL
- exact file title and exact file URL
- canonical `person_id`
- source identity anchor and review rationale
- creator/author
- license identifier and license URL
- required attribution/credit line
- commercial-use permission
- derivatives/crop/resize permission
- ShareAlike or other derivative obligation
- file revision timestamp
- file hash/checksum
- MIME type and dimensions
- source-rights evidence URL(s)
- rights checked timestamp
- identity reviewed timestamp
- reviewer/result
- status: `ELIGIBLE`, `NEEDS_RIGHTS_REVIEW`, or `REJECT`

This is a manifest shape, not a new Pydantic contract, table or public API. Do not add persistence
until one real pilot proves which fields must survive runtime and publication.

## Future display contract

If a later Portrait Pilot is approved, the public surface should:

- use the reviewed portrait only for the exact canonical Person;
- retain initials fallback for every Person without an eligible portrait;
- expose a compact image credit/source affordance rather than hiding attribution;
- preserve license and modification information required by the selected file;
- use a locally controlled reviewed asset rather than runtime search or arbitrary hotlinking;
- fail back to initials if the reviewed asset is unavailable rather than substituting another
  search result.

Portrait presence must not imply importance, endorsement, confidence, completeness or identity
quality.

## Explicit exclusions

This source gate does not:

- download or store any portrait bytes;
- hotlink an Assembly or Commons image in Civic Intel;
- modify `Person`, API DTOs or web types;
- add a media/portrait table, migration, object-storage bucket or image service;
- change SourcePolicy;
- add image-search or Commons crawling automation;
- use face recognition, image embeddings or biometric matching;
- create AI-generated portraits;
- redesign People or Person pages;
- change Railway, database contents, services, domains, variables or plan;
- claim broad portrait coverage for the 299-person directory.

## Source-gate conclusion

The portrait path is viable, but the two source classes have different gates:

- direct Assembly portrait: strong identity anchor, insufficient work-level rights evidence in the
  inspected page → `NEEDS_RIGHTS_CONFIRMATION`;
- Commons file imported from that Assembly portrait: explicit Commons license claim but unresolved
  source-work corroboration → `NEEDS_RIGHTS_REVIEW`;
- Commons file with reviewed external free-license history: viable manual pilot candidate when
  identity, attribution and derivative obligations are recorded → `ELIGIBLE_CANDIDATE`.

No image is approved merely because it appears on an official site or on Commons.

## Exactly one Next Best Action

Define `Portrait Pilot v0` around one manually reviewed `ELIGIBLE_CANDIDATE` Commons file. The
pilot should pin exact bytes/version evidence, implement the smallest attribution-aware portrait
read/display path, preserve initials fallback, and add deterministic identity/rights regressions.
Do not use the direct Assembly portrait until its work-level rights gate closes.
