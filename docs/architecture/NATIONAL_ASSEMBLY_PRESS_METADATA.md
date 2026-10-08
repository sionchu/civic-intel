# National Assembly official press metadata

This lane covers the Secretariat's official press resource, not external journalism,
authorship, quoted statements, allegations or universal Person news coverage.
The [official resource](https://open.assembly.go.kr/portal/data/service/selectAPIServicePage.do/OBX2DO001030E516625)
was rechecked through Aside on 2026-10-09. Its metadata panel declares KOGL attribution;
its output schema is NUM, TITLE, WRITE_DATE, CONTENT, CONTENT_URL and BBS_TITLE.
There is no authoritative Person identifier. Preserve the existing Assembly SourcePolicy,
including `can_send_to_ai=False`; licence metadata does not silently change that decision.

The existing connector retains only record key, title, written date, category and its exact
secret-free official record URL. `workers.assembly_press_import` accepts one supplied
metadata page with exact written date, page index, page size, total count and normalized records.
It performs no network request. SourcePolicy is checked before reading source metadata.
Default execution writes nothing and returns only hashes/counts/status, never titles or records.
An explicit capture commit requires complete stored-policy equality and the existing atomic
`commit_source_page` transaction; it cannot create or replace a policy.

SourceSnapshot owns the bounded page capture. FeederObservation retains only closed fields,
snapshot provenance and an immutable hash, with empty identity hints. Selected-page coverage
is not full-date, complete-source or complete-news coverage. NUM identifies a press record only.
CONTENT, CONTENT_URL, secrets, private fields and provider-supplied identity hints are rejected
at the normalized capture boundary; no fulltext or excerpt is retained.

`OFFICIAL_PRESS_SOURCE_CONTEXT` is accepted only for existing `LINK_PERSON`, never merge or
automatic identity creation. A genuine owner review of the actual record's Person relevance is
required in addition to a current, exact, published Assembly roster Evidence anchor. The roster
proves identity only; it does not establish article relevance. Titles/names are never compared
to authorize a link. Other public-person categories currently have no linkage adapter in this lane.
Same-key immutable version conflicts, incomplete capture runs and nonunique active links fail closed.

Linking creates a DRAFT, source-attributed CLAIM with SUPPORT evidence and a NEUTRAL copied roster
bridge. Separate PUBLISH recomputes source/identity/claim closure under the existing admin preview,
state hash, transaction and audit. Publication records the existence of reviewed official press
metadata; it never promotes its content to FACT. Public readers must validate this same immutable
closure and active Person link, and must not send the source metadata to AI.
Claim valid-from uses the source's written calendar day at KST midnight as a day boundary;
it is not a claimed publication timestamp. Source.published_at remains absent.

## Additional bounded catalogue review

Aside catalogue searches on 2026-10-09 returned three results for 보도, three for 의원실,
one for 발언 and one for 소식. The following real alternatives were inspected at schema level:

| Resource | Public API | Documented identity information | Current boundary |
| --- | --- | --- | --- |
| [의장단 보도자료](https://open.assembly.go.kr/portal/data/service/selectAPIServicePage.do/OOWY4R001216HX11434) | SPGRPPRESS | CHM_DIV, title, written date, LINK_URL; no MONA | Official source-context review required; title/office not Person ID |
| [의원실 행사 정보](https://open.assembly.go.kr/portal/data/service/selectAPIServicePage.do/OOWY4R001216HX11501) | NAMEMBEREVENT | NAAS_NM, event title/date/place, LINK_URL; no MONA | Name-only identity forbidden; exact official URL identity semantics unverified |
| [국회뉴스ON 의원실 행사](https://open.assembly.go.kr/portal/data/service/selectAPIServicePage.do/O4BV430009830710440) | nkulntiravezskrjd | title, article URL, modification/writing dates, V_BODY; no MONA | Possible source-specific metadata lane; no article-body acquisition or Person auto-link |
| [발언영상](https://open.assembly.go.kr/portal/data/service/selectAPIServicePage.do/O3VTTM0010223D15681) | npeslxqbanwkimebr | term/session/meeting/date/title/speaker text/runtime/LINK_URL; no MONA | Speaker text is not exact identity; video/transcript acquisition not performed |

The event, newsON and video metadata panels declare KOGL attribution. This is not an AI permission
change or proof of exact Person linkage. Robots was checked through Aside: HTTP 200, `Disallow: /admin/`.
The four additional APIs now have source-specific supplied-row metadata adapters in
`packages/connectors/open_assembly_activity_metadata.py`, connected to the existing worker with
`--activity-api SPGRPPRESS|NAMEMBEREVENT|nkulntiravezskrjd|npeslxqbanwkimebr`. Input is one finite
page envelope: page_index, page_size, list_total_count and records. The adapters retain only title,
an exact ISO source calendar date when available, safe printed speaker/name labels and credential-free,
query-free official links. Unknown date formats remain UNKNOWN. V_BODY, CONTENT, event venue,
unknown provider fields and credentials are discarded before canonical snapshot hashing/storage.
They perform no network calls, and metadata staging does not require or infer FETCH/AI permission.

Each adapter uses the same canonical SourceSnapshot/observation worker and strict stored-policy
matching on explicit capture commit. Current query/filter semantics, provider correction identity
and exact member URL anchor semantics remain unverified. Page ordinal is an explicitly staged
locator, not a stable provider identity. The snapshot carries `UNVERIFIED_NOT_FETCHED` query semantics
and `UNVERIFIED_PROVIDER_RECORD_LOCATOR`; LINK_PERSON/publication fail closed with
`PRESS_RECORD_LOCATOR_UNVERIFIED` even if a human selects a Person. No boolean supplied in a receipt
can bypass this missing source contract. Actual collection/canonical application/live coverage is NOT_RUN.

The additional routes are executable staged alternatives with pending immutable record identity,
query/correction contracts and exact Person context. Their existence means
the single press dataset's missing Person ID cannot establish that all Person news routes are absent.
This bounded catalogue review is not an exhaustive world-news or every-source audit.

Use `python -m workers.assembly_press_import --help` for the executable entry. Full owner previews
may be saved to a new local `--preview-output` file; their contents remain owner-local when AI is
disallowed. Tests use synthetic metadata and disposable migrated canonical databases. Actual
operational capture, linkage, publication and deployed coverage are separate evidence states.
