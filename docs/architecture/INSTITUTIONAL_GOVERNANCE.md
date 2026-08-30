# Institutional Governance

## Purpose

Civic Intel must represent public-service feeder paths that do not fit ordinary ministry,
legislature or private-company careers. Presidential commissions, temporary task forces,
public institutions, policy banks, state-linked listed companies, ownership stakes, boards
and executive-selection events are therefore first-class evidence-backed objects.

This layer models **formal governance facts**. It does not infer hidden political control.

```text
Person
  -> CommitteeMembershipEpisode / BoardSeat / CareerEpisode
  -> AppointmentPath / TalentPoolEntry

Organization
  -> InstitutionalBody
  -> OwnershipStake / GovernanceRelation
  -> GovernanceSelectionEvent / BoardSeat
```

## Boundary with private-sector feeder pools

A normal private company remains a normal `Organization` plus Corporate Career Facet. It is
not an `InstitutionalBody` merely because one of its executives later enters government.

Private-sector feeder discovery may include publicly documented directors, executives,
CTOs, research-center heads and other senior responsible leaders where public-interest
sources are sufficient. The preferred evidence ladder is:

1. OpenDART / statutory corporate disclosures when applicable
2. company official governance, IR, executive biography or press material
3. official government committee/event records that identify the person's public role
4. attributable news for discovery/context

Do not build employee rosters, private contact networks or non-public personnel lists.

A private-sector person discovered this way enters the same identity resolver and profiler
as any other Person.

## InstitutionalBody

`InstitutionalBody` classifies public/governance bodies without flattening distinct legal
forms.

Supported V0 categories:

- `PRESIDENTIAL_COMMISSION`
- `PRESIDENTIAL_ADVISORY_BODY`
- `GOVERNMENT_COMMITTEE`
- `TASK_FORCE`
- `SPECIAL_COMMITTEE`
- `PUBLIC_INSTITUTION`
- `POLICY_BANK`
- `STATE_LINKED_COMPANY`
- `PUBLIC_CORPORATION`
- `OTHER_PUBLIC_ENTITY`

A body is time-bounded and source-backed. Fields may include its legal basis, parent or
reporting organization and whether it is standing or temporary.

Examples of structurally different bodies:

```text
국가AI전략위원회  -> PRESIDENTIAL_COMMISSION
한국수출입은행    -> POLICY_BANK
KAI               -> STATE_LINKED_COMPANY when modeled through public ownership links
```

The category is a legal/governance description, not a political label.

## CommitteeMembershipEpisode

Committee, commission, advisory-body and TF service is a first-class career episode.

Fields:

- person
- institutional body
- public role such as chair, vice-chair, member, secretary or adviser
- validity interval
- standing/non-standing membership when known
- compensation only when publicly disclosed
- Claim/Source evidence

This permits evidence-backed feeder paths such as:

```text
private technology career
  -> policy adviser
  -> presidential commission vice-chair
  -> National Assembly
```

and:

```text
Presidential Office senior staff
  -> presidential commission leadership
```

Committee membership never implies personal closeness to the President unless separate
relationship evidence supports that claim.

## OwnershipStake

Ownership is modeled as a dated fact rather than an enduring label.

```text
owner
  -> OwnershipStake
      percentage / amount
      share class
      direct / indirect
      as_of
      source evidence
  -> target organization
```

An ownership chain may therefore be represented without collapsing it:

```text
Government/Public Entity
  -> policy bank
  -> listed company
```

Current ownership never overwrites historical ownership.

## GovernanceRelation

Only specific evidence-backed governance relations are permitted:

- `DIRECT_OWNERSHIP`
- `INDIRECT_OWNERSHIP`
- `LARGEST_SHAREHOLDER`
- `APPOINTMENT_AUTHORITY`
- `RECOMMENDATION_AUTHORITY`
- `BOARD_SELECTION`
- `STATUTORY_SUPERVISION`
- `BUDGETARY_SUPERVISION`

There is deliberately no generic `GOVERNMENT_CONTROLS` relation.

If a future UI wants to describe state influence, it must expose the underlying ownership,
statutory, appointment or board-selection chain and label any synthesized interpretation as
INFERENCE.

## GovernanceSelectionEvent

Executive and board selection mechanics are separate from political/campaign relationships.

A selection event records:

- target organization
- selected person or office
- event date
- explicit selection steps
- nominating/recommending/approving organizations when established
- appointing authority when legally established
- source evidence

Examples of steps may include:

```text
candidate recommendation
shareholder meeting approval
board resolution
statutory appointment
```

Do not convert a large public ownership stake into `government appointed the CEO` unless
formal selection evidence establishes that route.

## BoardSeat

A board seat is a dated relationship between a person and an organization's governing body.

Fields include:

- organization
- person
- board type
- role such as chair, representative director, inside/outside director or audit member
- linked GovernanceSelectionEvent when known
- source evidence

This lets the profiler distinguish:

```text
CEO / representative director
outside director
statutory institution head
policy-bank executive
```

rather than treating every senior title as the same relationship.

## Feeder-path integration

Institutional governance episodes feed the existing appointment model:

```text
Person
  -> CommitteeMembershipEpisode / BoardSeat / public-institution role
  -> CareerEpisode projection
  -> AppointmentPath
  -> AppointmentTarget / TalentPoolEntry
  -> Public Official Profiler
```

Useful descriptive queries include:

- presidential commission -> National Assembly
- Presidential Office -> commission leadership
- ministry/bureaucracy -> policy bank/public-institution executive
- military/defense bureaucracy -> state-linked defense-company CEO
- public-institution executive -> ministry/high public appointment

Historical frequency is descriptive and is never appointment probability.

## Evidence separation for sensitive narratives

The following must remain separate facts/claims:

```text
Person served on a presidential commission          FACT if officially documented
Person worked in an election campaign              FACT/CLAIM by source quality
Public entity is the largest shareholder           FACT with dated ownership evidence
CEO was elected by shareholder meeting/board       FACT with governance evidence
Government personally selected that CEO            separate FACT/CLAIM requiring evidence
Person is a political loyalist / faction member     CLAIM/INFERENCE, never implied by above
```

Administration turnover, resignation timing or campaign history cannot substitute for
selection-mechanism evidence.

## Source hierarchy

Prefer:

1. statute, presidential decree, official organization/appointment record
2. ALIO and institution official governance disclosures
3. OpenDART / KRX for listed-company ownership, executives and board filings
4. official shareholder-meeting, board, annual-report and IR disclosures
5. attributable news for discovery and context

All sources remain subject to SourcePolicy.

## Public-interest boundary

This ontology exists to explain publicly consequential staffing, governance and appointment
routes. It does not support:

- private donor or lobbying discovery
- private communications or contact graphs
- undisclosed family/business relationships
- speculative political control edges
- hidden ideology or loyalty scores
- employee-level private-company rosters

Every important public statement must remain traceable to Claim/Evidence/Source or a
source-backed governance contract staged for review.
