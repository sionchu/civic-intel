# Civic Intel — Agent Operating Model for Long-Term Batch Work

## Existing repository roles

현재 repo는 세 역할을 갖는다.

### Development

책임:

- canonical contracts
- deterministic implementation
- migrations
- smallest vertical slice

### Quality

책임:

- deterministic regression
- Golden Set
- evidence traceability
- identity isolation
- migration/behavior gates

### Risk Governance

책임:

- SourcePolicy
- privacy
- storage rights
- public-interest boundary
- uncertainty preservation

이 세 역할을 없애거나 새 agent framework로 교체하지 않는다.

---

# New specialization

새로 필요한 것은 별도 조직이 아니라 **batch ingestion skill**이다.

```text
.agents/skills/batch-ingestion-foundation/SKILL.md
```

이 skill은 Development role을 대체하지 않는다.

역할:

- source universe enumeration
- checkpoint/resume
- source run receipts
- policy-minimized observation
- identity materialization safety
- source-specific L3 acceptance

---

# Public Official Profiler role change

기존:

```text
feeder
→ ProfileResearchTarget
→ profiler
→ ReviewedPersonBundle
→ Person
```

가 사실상 onboarding path였다.

새:

```text
feeder
→ observation
→ identity
→ canonical Person
→ normal profile projection

selected high-value / complex person
→ ProfileResearchTarget
→ public-official-profiler
→ deeper evidence enrichment
```

즉 profiler는:

> batch ingestion agent가 아니다.

---

# Codex long-run loop

Codex는 한 번의 giant diff를 만들지 않는다.

다음 loop를 반복한다.

```text
READ
→ BASELINE
→ smallest coherent milestone
→ targeted tests
→ make verify
→ diff audit
→ coherent commit
→ update ExecPlan
→ continue
```

## READ

매 milestone 전:

- governing docs
- touched code
- nearby tests
- migration history

## BASELINE

현재 behavior를 테스트로 확인.

## IMPLEMENT

canonical artifact 수정.

## VERIFY

narrow → full.

## DIFF AUDIT

질문:

- duplicate path 생겼나?
- old path 남았나?
- unused abstraction 생겼나?
- docs와 code가 일치하나?
- source rights bypass가 생겼나?
- numeric identity shortcut이 생겼나?

## COMMIT

commit message는 현재 repository style을 따른다.

fix-up history를 길게 만들지 말고 milestone이 안정된 뒤 coherent commit.

---

# Decision authority

Codex가 routine choice는 직접 결정한다.

예:

- helper function naming
- test fixture filename
- SQLite temp DB location
- next migration revision
- small dependency-free refactor
- internal module move

사용자에게 재확인이 필요한 것:

- paid service
- destructive data deletion
- weakening privacy/security
- secret exposure
- public access broadening
- unclear rights인데 live crawling 강행

---

# Clean-v0 review vocabulary

최종 audit에서 발견사항은:

```text
KEEP
REMOVE
MERGE
RE0
```

그리고 priority:

```text
P0
P1
P2
```

로 본다.

## Typical P0

- wrong-person auto merge
- credential persistence
- SourcePolicy bypass
- published FACT without evidence
- checkpoint ahead of committed data
- irreversible broken migration

## Typical P1

- duplicate repository
- duplicate raw truth store
- docs maturity incorrect
- dead old path
- unnecessary abstraction

## Typical P2

- naming cleanup
- non-blocking docs polish
- optional operational metrics

---

# Long-run anti-bloat rules

추가 dependency는 기본적으로 금지.

이번 milestone에 필요한 것은 현재 stack:

```text
Python
Pydantic
SQLAlchemy
Alembic
httpx
pytest
FastAPI
```

로 충분하다.

다음은 실제 필요가 측정될 때만:

- Splink
- queue
- scheduler
- MCP
- search index
- graph DB

---

# Completion behavior

Codex는 stop condition 완료 전:

> “다음에 할까요?”

로 매 milestone마다 멈추지 않는다.

계속 진행한다.

단 실제 blocker는 즉시 기록하고 가능한 다른 milestone을 진행한다.

최종 보고는 증거 기반으로:

- local test
- CI
- migration
- commit

을 구분한다.
