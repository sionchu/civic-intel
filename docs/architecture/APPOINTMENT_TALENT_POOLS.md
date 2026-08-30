# Appointment Targets and Talent Pools

## Purpose

Civic Intel should explain not only **who currently holds an office**, but also which public
career paths and documented experience make a person relevant to a future appointment.

The talent-pool layer is evidence-backed and role-specific. It is not an endorsement,
political desirability score, or prediction that the appointing authority is actually
considering a person.

```text
Person
  -> Career Facets / Claims / Evidence
  -> AppointmentTarget
  -> TalentPoolEntry
       -> RoleFitEvidence[]
```

One person may appear in several target pools at the same time.

## AppointmentTarget

An appointment target describes the office, appointment route and observable role-fit
dimensions. Targets are time-bounded because ministries, Presidential Office structures
and appointment rules can change.

Required contract properties:

- stable slug
- office title and institution
- appointment route
- personnel-hearing requirement when known
- role-fit dimensions
- official/legal source IDs supporting the target definition
- validity interval

Do not infer the appointment route from title alone.

## TalentPoolEntry

A talent-pool entry answers one question:

> Why is this person structurally relevant to this office, based on public evidence?

It contains:

- person and appointment-target IDs
- one structural bucket
- explicit inclusion reason
- dimension-by-dimension evidence/gaps
- optional claim ID only when there is actual public evidence that the appointing authority
  is considering the person

There is deliberately no appointment-probability field.

## Structural buckets

- `DIRECT_FEEDER`: current/recent occupation of a historically adjacent office
- `DOMAIN_SENIOR`: senior sustained experience in the office's policy domain
- `POLITICAL_EXECUTIVE`: substantial political and cross-government executive coordination
- `TECHNICAL_EXPERT`: deep research/technical/domain expertise relevant to the office
- `EMERGING`: relevant evidence exists but seniority/leadership coverage remains incomplete

A bucket is descriptive, not a rank.

## Role-fit evidence status

Each dimension uses one of:

- `EVIDENCED`: direct public evidence supports the dimension
- `PARTIAL`: relevant evidence exists but coverage is incomplete
- `UNKNOWN`: the system cannot establish the dimension
- `GAP`: available evidence indicates the expected dimension is not present or not yet held

`EVIDENCED` and `PARTIAL` require a Claim or Source reference. `UNKNOWN` and `GAP` require
an explanatory note.

## Target registry groups

### Cabinet / ministerial targets

Examples include:

- 국방부 장관
- 외교부 장관
- 통일부 장관
- 법무부 장관
- economy/finance, industry, science/technology, welfare, education and other ministers

Cabinet-member candidates are handled as a distinct appointment route because the National
Assembly Act's personnel-hearing framework applies to `국무위원` candidates.

### Presidential Office targets

The current official Presidential Office organization (reviewed 2026-08-30) includes:

- 대통령비서실장
- 정책실장
- 국가안보실장
- 정무수석
- 민정수석
- 인사수석
- 경제성장수석
- 사회수석
- AI미래기획수석
- 홍보소통수석
- 경청통합수석
- 외교안보특별보좌관
- 국가안보실 차장 and security/defense/diplomacy/unification/economic-security/cyber lines

The registry must not assume a Presidential Office structure remains unchanged across
administrations.

### Other high public appointments

Future targets include legally distinct appointments such as:

- 국가정보원장
- 공정거래위원장
- 금융위원장
- 국세청장
- 검찰총장
- 경찰청장
- 합동참모의장
- 한국은행 총재
- other statutory presidential/high-public appointments

Each target stores its own appointment/hearing route.

## Common evidence dimensions

Targets may select from observable dimensions such as:

- policy-domain experience
- executive/organizational leadership
- public-service seniority
- legislative/political experience
- crisis/incident command
- inter-agency coordination
- international/defense/security experience
- academic/technical expertise
- corporate/industry experience
- recent relevant activity
- adjacent-office history
- public hearing/controversy/unresolved-risk evidence

No dimension is automatically required for every appointment.

## 국방부 장관 target

Suggested observable dimensions:

1. `defense_security_domain`
   - sustained defense/security policy work
2. `command_or_defense_executive`
   - documented military command, Ministry of National Defense, Joint Chiefs or equivalent
     civilian defense executive experience
3. `force_planning_acquisition`
   - force planning, acquisition, defense industry or capability-development responsibility
4. `alliance_international_security`
   - alliance, diplomacy or international-security responsibility
5. `legislative_defense`
   - sustained National Assembly defense-committee or relevant legislative activity
6. `civilian_policy_expertise`
   - defense/security academic or research leadership
7. `crisis_coordination`
   - documented national-security crisis or inter-agency coordination
8. `organizational_leadership`
   - leadership of a large public organization or equivalent

Possible feeder categories include retired senior military officers, defense/security
bureaucrats, National Security Office officials, lawmakers with sustained defense portfolios,
diplomats/security academics and other documented defense-policy leaders.

These are feeder categories, not eligibility rules. Military service is not automatically
preferred, and civilian expertise must not be discounted by the model.

## 대통령비서실장 target

The Chief of Staff coordinates the Presidential Secretariat under the President's direction.
The role is therefore modeled separately from a cabinet minister.

Suggested observable dimensions:

1. `presidential_executive_staff`
   - senior Presidential Office, Prime Minister's Office or ministerial staff/executive work
2. `political_coordination`
   - documented National Assembly, party, coalition or high-level political coordination
3. `cross_ministry_coordination`
   - cross-government policy/implementation coordination
4. `organization_personnel_management`
   - senior personnel or large-organization management
5. `campaign_party_leadership`
   - publicly documented senior campaign/party leadership where relevant
6. `trusted_advisory_role`
   - documented repeated senior advisory or appointment relationship
7. `crisis_messaging_coordination`
   - crisis coordination, public messaging or situation-room responsibility

Labels such as `측근`, `복심`, or `친○○` are not FACT merely because they are repeated in
news coverage. Preserve the original actor/source as CLAIM, or use INFERENCE only when the
relationship evidence satisfies repository rules.

## 국가안보실장 target

Suggested dimensions:

- foreign/security strategy
- NSC/National Security Office experience
- diplomacy/defense senior leadership
- alliance/North Korea strategy
- economic-security/cyber expertise where relevant
- inter-agency crisis coordination

## 정책실장 target

Suggested dimensions:

- cross-domain policy design
- economic/social/budget coordination
- senior ministry/research-institute/Presidential Office leadership
- implementation of major government agendas
- inter-ministry coordination

## Historical AppointmentPath reference set

Talent-pool structure should gradually be grounded in past appointments rather than intuition.
For each historical officeholder, collect:

- target office
- appointment date / end date
- immediately previous role
- three to five prior significant roles
- administration/context
- time from feeder role to appointment
- source evidence

Example projection:

```text
AppointmentPath
person_id
appointment_target_id
appointed_at
prior_roles[]
immediately_prior_role
source_ids[]
```

Historical frequency is descriptive. It must never be presented as an appointment
probability.

## Actual consideration vs structural relevance

These must remain separate:

```text
STRUCTURAL TALENT POOL
public career evidence makes the person relevant to the target

ACTUAL CONSIDERATION
an official statement or attributable report says the appointing authority is considering
that person
```

A `TalentPoolEntry` does not imply actual consideration. Actual consideration requires an
explicit Claim reference.

## Site views

Future routes may include:

- `/offices`
- `/offices/minister-national-defense`
- `/offices/chief-of-staff`
- `/offices/national-security-adviser`
- `/talent-pools/defense`

A target-office page should show:

- role authority and appointment route
- personnel-hearing requirement
- current and historical holders
- common historical feeder paths
- talent-pool entries grouped by structural bucket
- evidence coverage and gaps for each person
- recent changes
- full source/audit links

## Risk rules

Never infer or publish from this layer:

- that a person is actually being considered without evidence
- partisan desirability or ideological suitability scores
- private political contacts or private communications
- private family/network information
- psychographic/personality rankings
- hidden protected/sensitive-trait scores

Controversy volume is not guilt. Faction/network similarity is not an appointment fact.

## Source basis reviewed 2026-08-30

- Current Presidential Office organization: https://www.president.go.kr/organization
- National Assembly Act personnel-hearing framework: 국가법령정보센터, 국회법 제65조의2
- Presidential Secretariat rules: 국가법령정보센터, 대통령비서실 직제

These source statements must be converted to normal Source/Claim/Evidence records before
being published as product facts.