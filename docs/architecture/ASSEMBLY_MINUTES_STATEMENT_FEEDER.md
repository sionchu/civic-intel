# Assembly Minutes Statement Feeder

Status: L2 SINGLE_PULL (human-assisted exact-PDF packet path). Audit date: 2026-10-05.

This lane turns one exact official National Assembly **committee minutes** PDF (국회 회의록) into
ordered speaker-turn `FeederObservation` rows. It is a statement *source* lane under the AGENTS.md
"Statement and curated-source ingestion" rules: the minutes are the primary official record, so
no discovery source or curated compilation participates.

It does **not** create or link Persons, publish Claims, label statements (lie, flip-flop,
contradiction), use model assistance, or expose any public UI.

## Sources

| Role | Source | Access decision |
|---|---|---|
| Meeting metadata | 열린국회정보 Open API `ncwgseseafwbuheph` (위원회 회의록), `https://open.assembly.go.kr/portal/openapi/ncwgseseafwbuheph`; also data.go.kr 15126038 | Official API. The Secretariat API guide (오픈API활용가이드_국회사무처) lists 이용허락범위 "제한 없음". `open.assembly.go.kr/robots.txt` disallows only `/admin/`. Required arguments include `DAE_NUM` and `CONF_DATE`; the keyless `sample` mode is fixed to `pIndex=1`, `pSize=5` |
| Statement text | `https://record.assembly.go.kr/assembly/viewer/minutes/download/pdf.do?id=<CONFER_NUM>` | `record.assembly.go.kr/robots.txt` returned HTTP 404 on 2026-10-05. Not having robots rules is not treated as an automation contract. The importer never fetches: the operator supplies the exact PDF bytes |

A 2026-10-05 keyless sample call (`DAE_NUM=22&CONF_DATE=2026-09-28`, 5 rows) returned one row per
agenda item with `CONFER_NUM`, `TITLE`, `CLASS_NAME`, `DAE_NUM`, `COMM_NAME`, `VODCOMM_CODE`,
`CONF_DATE`, `SUB_NAME`, `VOD_LINK_URL`, `CONF_LINK_URL`, `PDF_LINK_URL`, `PDF_FILE_ID`, `DEPT_CD`
and `CONF_ID`. `PDF_LINK_URL` carries `id=<CONFER_NUM>`. `CONF_LINK_URL` (`xml.do?...&type=summary`)
returned an HTML viewer page, not a structured XML transcript, so the PDF stays the text source.

The plenary (`nzbyfwhwaoanttzje`), whole-house committee (`ngytonzwavydlbbha`) and subcommittee
minutes services exist but are out of scope for this slice.

## SourcePolicy

`record.assembly.go.kr`, source class `official_national_assembly_minutes`:

| Flag | Value | Reason |
|---|---|---|
| `can_fetch` | false | human-assisted capture only |
| `can_store_metadata` | true | meeting identity, locators, hashes |
| `can_store_fulltext` | false | no whole-document text in `SourceSnapshot`; no raw republication |
| `can_send_to_ai` | false | model assistance is not used |
| `can_show_excerpt` | true | per-turn exact excerpts of the speaker's own words |
| `can_commercialize` | false | not reviewed |

Basis for retaining per-turn excerpts: the record is published by statute (국회법 제118조 회의록
반포); 저작권법 제24조 lets anyone use statements made publicly in the National Assembly "by any
method"; and the minutes are a state work-for-hire (저작권법 제24조의2 공공저작물 자유이용).
Statute and meeting text were checked at this level only; this is not a legal opinion.

The 제24조 proviso excludes *compiling the same speaker's statements*. Storing turns per meeting is
not that compilation, but a per-speaker display or export would be. That, any Claim publication
and any linking of speakers to Persons are **open owner/legal decisions**. If `can_show_excerpt`
is false the importer still writes locators, `quote_sha256` and `quote_char_length`, and stores
`quote_text = null`. If `can_store_metadata` is false it refuses to build the capture.

## Packet and import

`assembly-minutes-packet.v1` (see `tests/fixtures/assembly_minutes_synthetic_packet.json`):

- `acquisition_channel = OPERATOR_SUPPLIED_OFFICIAL_PDF`, `received_via`, `artifact_sha256`;
- `api_rows`: the meeting's Open API rows, unchanged (unknown fields are rejected). All rows must
  agree on meeting fields. `TITLE` must agree with `DAE_NUM`, `COMM_NAME` and `CONF_DATE`, and
  `PDF_LINK_URL` must be exactly
  `https://record.assembly.go.kr/assembly/viewer/minutes/download/pdf.do?id=<CONFER_NUM>`
  (no other query keys, so no credentials).

`civic-import-assembly-minutes --packet P --artifact PDF --confirm-official-minutes-copy`
runs as a dry run by default. `--commit --database-url URL` writes Source/SourceSnapshot/
FeederObservation through the shared `commit_source_page`. The importer:

1. verifies the PDF's sha256 against the packet (mismatch → refuse);
2. extracts the layout-mode text layer with `pypdf` (optional extra `minutes-pdf`, imported
   lazily) and records the extractor identity and `text_layer_sha256`;
3. parses turns and checks that the page header session/sitting/date/committee and every API
   `SUB_NAME` match the minutes;
4. writes one snapshot (`content_hash` = raw PDF sha256, `fulltext = null`) and one observation
   per turn.

- Feeder: `assembly_minutes_speaker_turns`.
- Scope: `{DAE_NUM}:{CONFER_NUM}:{parser_revision}`.
- Record key: `{CONFER_NUM}:{turn_ordinal}`.
- Checkpoint cursor: `{pdf_sha256}:{parser_revision}:{turns_hash}`.

A parser revision change opens a new scope, so earlier observations are not overwritten. Re-running
the same artifact gives `observations_unchanged` and reuses the snapshot. `identity_hints` is always
`{}` and `speaker_person_link` is always `null`.

`pypdf` is the only added dependency. It is an optional extra, not a runtime requirement, because
deterministic PDF text-layer extraction (CID fonts with ToUnicode maps) cannot reasonably be
reimplemented. Tests replace the extractor and do not need it.

## Parser (`assembly-minutes-turns.r1`)

Text layer facts observed on five official 2026-09 committee minutes (76 pages): the PDF draws no
space glyphs. Default `pypdf` extraction concatenates glyphs and sometimes puts the cover box after
the body. Layout-mode extraction restores reading order and lines, with the same glyph multiset on
every page, but its spaces are inferred from geometry and are wrong in places (`정 비하는`,
`바 꾸는`). So:

- **Text form `PDF_GLYPH_SEQUENCE_NO_WHITESPACE`.** Every stored text value is the exact glyph
  sequence with all whitespace removed. Spaces are never re-inserted, lines are joined without
  inserting characters, nothing is de-hyphenated, and Hanja compatibility ideographs (e.g.
  U+F9E1) are kept unnormalized. English words lose their spaces (`citycouncil`). The quote
  boundaries are exact on the glyph stream, but the text is **not display-ready prose**: a spaced
  rendering needs another official text route (HWP download or viewer), which is an open decision.
- **Page headers.** Each page must start with `제N회-<committee>제N차(YYYY년M월D일)` plus exactly one
  printed page number, either before or after it. The headers must agree and the page numbers
  must be consecutive from 1, otherwise the parse fails.
- **Body bounds.** The body runs from exactly one `(HH시MM분개의)` to exactly one `(HH시MM분산회)`.
  The cover before it supplies the `상정된 안건` index. The appendix after it is excluded
  (출석위원/청가 lists, 보고사항, 제안설명서, petition referrals). An appendix label such as
  `◯출석 위원` inside the body fails the parse.
- **Speaker turns.** A turn starts at a `◯` line. The printed label must parse uniquely as
  `<name> 위원|의원` or `<role> <name>`. A role is 위원장/진술인/증인/참고인/staff titles, or a
  government title matched by suffix across up to two layout tokens. A name is 2–4 Hangul or
  Hanja glyphs. Each turn stores `speaker_label_raw` as glyphs, plus `speaker_role_printed` and
  `speaker_name_printed` as text. `speaker_role_category` is a derived label from the printed
  role only.
- **Stage directions.** Whole-line parenthesized lines (`(「예」하는위원있음)`, `(14시07분)`,
  `(제안설명서는끝에실음)`) and a speaker line whose remainder is one parenthesized group
  (`(손을듦)`) are stored in `stage_directions`, never in the quote. They split the quote into
  `segments`; `quote_text` joins the segments with a newline. Inline parentheses inside speech
  stay in the quote as printed and set `contains_inline_parenthetical`.
- **Agenda headings.** A heading line follows a blank line (or continues a heading block that takes
  several items together), exactly equals the next index entry (it may wrap over lines), and
  appears in index order. An index entry out of order, or text with no open turn, fails the parse.
- **Locators.** Each turn records printed `page_start/page_end`, PDF `pdf_page_start/end`,
  `agenda_items` and `last_time_marker` (the latest printed `(HH시MM분)` at or before the turn).

## Evidence

- Five real minutes from the owner-supplied merge (운영 제1차, 행안 제3차, 문체 제3차, 기후노동
  제3차, 국토 제4차; pages split per meeting): r1 parsed 16 + 215 + 50 + 31 + 16 = 328 turns
  with no failures (pypdf 5.9), after two fixes this check found: grouped agenda headings and
  Hanja compatibility ideographs.
- One bounded official download, made only to verify this boundary (`pdf.do?id=57370`, 행정안전위원회
  제439회 제3차, 36 pages, sha256 `582d8845…ba46e`), with its three API rows as the packet: dry run
  gave 215 turns (pypdf 6.19). A commit into a disposable SQLite database created 215
  observations and one snapshot with `fulltext` null. Re-running it created 0 and left 215
  unchanged, reusing the same snapshot. 0 Person and 0 Claim rows.
- Committed fixtures are synthetic: no real meeting, speaker or petitioner.

## Maturity and limits

- L2 SINGLE_PULL: the human-assisted single-packet boundary is implemented with exact-byte
  verification, a deterministic parser, an idempotent commit and checkpoints.
- Not L3: there is no enumeration of the minutes universe (the Open API supports date
  enumeration, but there is no automated PDF route), no plenary or subcommittee formats, and no
  correction/version contract for re-issued PDFs (a new sha256 becomes a new snapshot).
- Speakers include non-official 진술인/증인/참고인, whose printed labels are stored as printed.
  Whether to withhold their labels or quotes is an open owner decision.
- Multi-sitting minutes (차수변경, more than one 개의/산회) and two-column layouts fail closed in r1.
