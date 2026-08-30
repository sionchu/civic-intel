# Gwanbo Personnel Feeder

## Scope

This feeder enumerates the complete result set for one explicit publication-date window in
the Ministry of the Interior and Safety electronic-gazette personnel list.

It records official personnel **notice metadata**. It does not infer a named person,
appointment, promotion, transfer or `CivilServiceCareerEpisode` from a notice title.

```text
explicit date window (maximum three years)
 -> official personnel list pages
 -> metadata-only FeederObservation
 -> no automatic Person materialization
```

The bounded scope key is:

```text
YYYY-MM-DD:YYYY-MM-DD
```

The date window, page size, total count and expected page count are retained in the source
checkpoint.

## Official contract review

Reviewed on 2026-08-31:

- public UI: `https://open.gwanbo.go.kr/OpenApi/web/personnelList`
- list endpoint: `POST https://open.gwanbo.go.kr/OpenApi/web/personnelListAjax`
- theme selector: `themaSe=06`
- bounded inputs: `reqFrom`, `reqTo`
- paging inputs: `currentPage`, `rowPerPage`
- provider record identifier: `cntntSeqNo`, exposed by the page's `fnDetail` contract
- list fields: title, publication date, gazette name, compilation type, publication
  institution, basis law, revision reason and detail path
- authentication: none exposed or sent by the official page
- published rate limit: none stated; the implementation is sequential and date-bounded
- reuse license: none stated on this API page; the footer says all rights reserved

The official page currently returned zero personnel results both for its default three-year
window and for a wider interactive date query. That live result is evidence of current source
behavior, not evidence that the provider universe is permanently empty. Multi-page coverage is
verified offline against deterministic responses matching the published page contract.

## SourcePolicy

`gwanbo_personnel_policy()` permits only:

```text
FETCH
STORE_METADATA
```

It blocks:

```text
STORE_FULLTEXT
SEND_TO_AI
SHOW_EXCERPT
COMMERCIALIZE
```

Raw HTML, original-file URLs and original document bodies are not retained. The page-body hash
still supports immutable source snapshots without storing the body.

This conservative policy is independent of other datasets on data.go.kr. A reuse license on a
different electronic-gazette analysis file is not transferred to this HTML POST interface.

## Normalized observation

Allowed normalized fields:

```text
notice_id
title
publication_date
gazette_name
compilation_type
publication_institution
basis_law
revision_reason
detail_path
```

`identity_hints` is intentionally empty. The source list does not expose a structured person
name or exact personnel action.

Excluded:

```text
original file URL
print/original flags
raw HTML
guessed person name
guessed office or rank
guessed CivilServiceEventType
```

## Coverage and resume

The enumerator uses the same canonical batch persistence as Assembly:

```text
SourcePolicy
 -> Source
 -> SourceSnapshot
 -> FeederObservation
 -> SourceCheckpoint
 -> SourceRun
```

It fails closed on:

- response date-window/page mismatch;
- missing or changing total count;
- incomplete page length;
- duplicate page content;
- duplicate or conflicting `cntntSeqNo`;
- final unique-count mismatch.

Each page and its checkpoint commit in one repository transaction. A later failure leaves a
`PARTIAL` run and the last committed page can be resumed. Unchanged reruns reuse observations;
changed normalized metadata creates a new immutable observation version.

## Career semantics

This first L3 slice stops at official notice discovery because the list contract does not
provide structured person/event fields. A later detail-document adapter may create a
`CivilServiceCareerEpisode` only when it can preserve an exact named person, agency, title,
effective date and explicit personnel action from reviewed official fields.

The absence of those fields is never filled by title parsing or a model-generated guess.
