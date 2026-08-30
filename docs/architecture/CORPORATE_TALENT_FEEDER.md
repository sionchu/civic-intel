# Private-Sector Senior Talent Feeder

## Purpose

Civic Intel discovers publicly consequential private-sector leaders whose documented careers
may later connect to commissions, public institutions, elected office, the Presidential
Office or high public appointments. It is **not** an employee directory.

Two evidence lanes remain distinct:

```text
OpenDART statutory disclosure
 -> disclosed executive / compensation / ownership metadata

company official profile
 -> publicly named senior technical/business responsibility
```

Both can feed the same Person identity after Identity Resolution, but neither silently
replaces the other.

## OpenDART lane

Reviewed official APIs include:

- `exctvSttus`: executive status;
- `hmvAuditIndvdlBySttusV2`: individual director/auditor compensation over the statutory
  disclosure threshold for reports submitted from May 2026 onward;
- `indvdlByPayV2`: top individual compensation disclosures over the statutory threshold;
- `elestock`: officer / major-shareholder ownership reports.

OpenDART states that these APIs expose information extracted from disclosure documents
submitted by companies and that the Financial Supervisory Service does not guarantee the
accuracy/completeness of the submitted information. Therefore `rcept_no` is retained as the
canonical pointer back to the original disclosure.

### Executive status

The executive-status API exposes fields such as:

- name;
- birth year/month;
- position;
- registered/non-registered executive status;
- full-time/non-full-time status;
- assigned responsibility;
- reported major career;
- largest-shareholder relationship;
- disclosed tenure period and tenure end;
- settlement date;
- receipt number.

Both registered and disclosed non-registered executives can enter the senior-person staging
lane. Ordinary employee APIs are intentionally out of scope.

`main_career` is a company-submitted disclosure field. It is a discovery/attribution fact,
not independent verification of every prior career episode.

### Compensation

Individual compensation disclosures are evidence of a disclosed compensation amount for a
specific reporting period. They are **not**:

- total wealth;
- current net worth;
- automatic evidence of executive seniority;
- automatic evidence of public-service relevance.

The top-five compensation API can include employees who are not senior executives.
Therefore compensation rows do not create a new Person candidate by themselves. They can be
linked only after a separate senior-role identity source such as executive status or a company
official profile is resolved.

### Officer / major-shareholder ownership

Ownership reports may identify a reporter as an officer and/or major shareholder and disclose
specific-security counts/rates. These are dated statutory disclosures.

They do not automatically establish:

- total personal wealth;
- effective control of the company;
- a conflict of interest;
- a political relationship;
- an appointment motive.

Any conflict or influence claim requires a separate predicate and evidence.

## Company-official-profile lane

Important public technical/business leaders may not appear as DART registered executives.
Examples can include CTOs, research-institute heads, AI/technology-center heads and major
business-unit heads.

A normalized company-official profile may create an IdentityCandidate only when:

- the role is senior and publicly consequential;
- the company itself publicly identifies the person and role/responsibility;
- the exact source domain has a reviewed SourcePolicy reference;
- the source is HTTPS and domain-consistent.

Allowed first-pass scopes are CEO/president, registered director, CTO/CSO/CIO, research
institute head, technology center head, major business-unit head and similarly reviewed
senior roles. Ordinary staff must fail closed.

The first PR does not contain a generic company-site crawler. Each company source remains
subject to its own SourcePolicy and source-specific collection decision.

## Performance attribution

Company performance and a person's causal contribution are separate claims.

```text
FACT
A served as CEO during 2024-2026.

FACT
Company revenue/orders rose during 2024-2026.

INFERENCE / CLAIM unless separately supported
A caused that increase.
```

Company official materials may support a narrower attributed responsibility such as “led the
AI center” or “was responsible for business X.” News repetition alone does not convert a
personal-performance claim into FACT.

## Privacy / roster boundary

Do not collect or emit:

- ordinary employee directories, including OpenDART employee-status data for person discovery;
- private HR data;
- personal phone/email/address;
- family/private-network data;
- private social-media information;
- non-public compensation;
- inferred clients/customers or personal business relationships.

## SourcePolicy boundary

OpenDART's official service is free and available to approved individual/company users, and
its terms defer copyright/public-data matters to applicable law. V0 allows credentialed
metadata fetch but keeps fulltext, AI use, excerpt display and commercial reuse fail-closed
until the intended deployment/use is separately reviewed.

Credentials are injected only into the outbound request and never persisted in discovery
URLs, metadata or errors.

## First implementation

- live-capable credential-safe OpenDART corporate connector;
- executive-status staging into existing `IdentityCandidate`;
- compensation enrichment without Person creation;
- officer/major-holder ownership staging with explicit semantic limits;
- normalized reviewed-company-profile lane for non-DART senior technical/business leaders;
- deterministic offline fixtures/tests;
- no automatic DB upsert/publication;
- no generic company crawler;
- no company-performance-to-person causal attribution.

The next best corporate step after this staging layer is to select one real high-public-
interest company/person case and verify `DART disclosure + company official profile + later
public role` end to end through the existing profiler.
