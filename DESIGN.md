# Civic Intel Design System

## Design intent

Civic Intel is a Korean-first public-governance evidence encyclopedia, presented as 모두의국감.
The interface helps a reader discover people, institutions, public careers, activities and
documented connections, then inspect the record behind each claim. 국정감사 2026 is an entry point,
not the permanent boundary of the product. The visual tone is precise and content-first, closer to a public-service
page (GOV.UK Frontend, TheyWorkForYou) than to a product landing page.

## Design principles

- Make the evidence path visible: identity, epistemic status, source and audit details stay
  adjacent to the rendered item.
- Use restrained editorial hierarchy: typography and whitespace establish importance; color
  communicates status, not persuasion.
- Keep unresolved states legible: `UNKNOWN`, `PARTIAL`, review and conflict states are explicit
  UI outcomes, not empty placeholders.
- Prefer one clear next interaction: open a profile, jump to a section or inspect a source.
- Keep the public surface read-only and source-bounded; do not add controls that imply approval,
  merging or publication authority.
- Make the reading path apparent through hierarchy and proximity: person → public record → Claim
  → Evidence → Source.
- Use whitespace, thin dividers and type to establish hierarchy. Use color for semantic feedback
  only, with one restrained civic accent.
- Prefer flat editorial rows and grouped fields over galleries, dashboards or nested cards.
- Say what is shown in as few words as possible. The record, its status chip and its source link
  carry the explanation; prose does not repeat it.

External design references may inform this grammar, but they do not override product behavior,
evidence rules, accessibility or existing component conventions. No external brand assets, copy,
fonts, icons, screenshots or proprietary tokens are part of this system.

## Foundations

### Color roles and semantic tokens

The light theme uses these roles in `apps/web/app/styles.css`:

- `--color-canvas`: neutral cool-gray page background; `--color-surface` is white.
- `--color-surface` / `--color-surface-muted`: primary and secondary panels.
- `--color-ink` / `--color-ink-muted`: primary and supporting text.
- `--color-line` / `--color-line-strong`: quiet and emphasized borders.
- `--color-accent` / `--color-accent-soft`: navigation, links and positive traceability cues.
- `--color-warning` / `--color-warning-soft`: claims, review and partial states.
- `--color-danger` / `--color-danger-soft`: refute, conflict and service-failure states.
- `--color-focus`: keyboard focus ring.

Text tokens meet WCAG AA (4.5:1) on every surface they are used on: `--color-ink-muted` `#5c6862`
is ≥4.9:1 on canvas, surface and surface-muted, and `--color-warning` `#8c5800` is ≥5.0:1 on the
same set. Placeholders use `--color-ink-muted`, never a lighter gray. Input and select borders use
`--color-line-strong` `#7d8791` (≥3.3:1, the WCAG non-text minimum is 3:1). Re-check this table whenever a
token changes.

Status colors are semantic only: green is not a confidence score, amber is not a risk score and
red is not a wrongdoing claim. `UNKNOWN` is a neutral unresolved evidence state, not an error;
transport failure and source conflict use distinct feedback treatment and language.

### Typography

Use one Korean-safe sans stack for everything: headings, names, body text, controls and dense
evidence metadata. Do not mix in a serif display face. Size floors follow
the KRDS numeric scale (principles only; no KRDS assets or government identity):

- No text below 13px anywhere, including chips, micro labels and table metadata.
- Body copy is 17px with 1.65 line height; supporting copy 15px; dense metadata 13px.
- Page `h1` is capped at `clamp(…, …, 3.75rem)` (60px); section headings at 2.5rem (40px).
- Letter spacing stays between -0.02em and 0.01em; no `text-transform: uppercase`.
- Numbers use `font-variant-numeric: tabular-nums` (set on `body`) and `Intl.NumberFormat("ko-KR")`.

Public labels and summaries are Korean-first, and readers see Korean predicate labels
(`apps/web/app/predicate-labels.ts`) instead of predicate codes such as `NOMINATED_AS`.
Public status, evidence and source headings use Korean display labels from the canonical UI mappings.
Internal enum values, DTO names and IDs stay unchanged; optional evidence details retain exact identifiers
beside Korean labels. Original source quotations, names and license identifiers remain faithful to the source.

### Spacing scale

Use a 4px base with recurring values of 8, 12, 16, 24, 32 and 48px. Dense evidence rows use
8–12px gaps; page regions use 32–64px. Avoid new arbitrary spacing values unless a content-driven
breakpoint requires one.

### Layout and containers

The content container is capped at 1180px with fluid 20–48px gutters. Home opens with the product
identity, one sentence and name search, followed by a source-backed audit-plan brief and working
exploration links in two columns that collapse to one. Brief rows show their plan date, source
publication date and direct Claim path; never select arbitrary people as recommendations.
People uses a readable directory column with flat
editorial rows and one mobile column. Profile pages keep their narrow index beside a readable
content column and reflow below 820px. Long Korean values and identifiers wrap instead of clip.

### Borders, radii, shadows and surfaces

The default surface uses a 1px border and no shadow (`--shadow-card: none`). Corners are 4–6px
and limited to controls, groups and feedback panels. Functional elevation may be used sparingly for an explicit
interactive surface. Avoid glass effects, heavy gradients and decorative depth that could make
source status feel more authoritative than the evidence.

## Components

### Records and panels

Roster records are flat rows: the canonical name as an underlined link, one line of the evidenced
role/party/district/committee values that exist (missing values are omitted, not repeated as
"정보 없음"), and evidence/as-of metadata. No initial avatars or arrow badges. Profile claims and sources are separate
panels. Public review displays remain read-only. The explicitly enabled private admin workspace uses
selected-record review, before/after previews, final confirmation and server-acknowledged receipts.
Operational IDs and full audit details remain expandable; mutation success is never optimistic.
Functional timelines, record panels and bounded graphs may expose eligible evidence, dates and
relationships using the existing tokens. Available records precede compact coverage notes.
Assembly discovery-filter gaps are not missing-person-record counts; clearly name the filter
scope and retain every public Person in unfiltered name search.

### Reviewed portraits

Portraits are an optional Person-detail presentation asset only. A portrait is displayed only
after an individual file-level rights review and an exact binding to a resolved canonical Person
ID; the visible creator, source-file and license links remain beside the image. The local copy
keeps the reviewed aspect ratio without an additional crop and shows nothing in its place when
the review is absent or withdrawn. Portrait coverage has no semantic
meaning, is not used by directory search, and never comes from face recognition, a generated
likeness or a name-only match.

### Navigation

The global header exposes the public directory only. Profile-local navigation is an anchor list
of the existing projection sections. The internal review route is not advertised in public
navigation.

### Tables and data-dense UI

People are presented as stacked readable rows rather than a gallery or wide table. Evidence is
presented as stacked readable rows. Source titles and policy summaries are visible; UUIDs, hashes
and snapshot references stay behind `details` disclosure.

### Status and feedback

Use Korean display labels for the existing domain states, preserving their distinct semantics and internal codes.
Status never relies on color alone: `.status` chips also carry a decorative shape (✓ resolved or
supported, ◇ claim/review/partial, ? unknown or unresolved, ! conflict or service failure) with empty
alt text, so the text label remains the accessible name.
Empty states explain what is absent without implying a negative fact.

Public reads distinguish an empty eligible result, a missing public record, insufficient comparison
inputs, source/version conflict, access denial and temporary service failure. A service failure must
not render as `UNKNOWN`, an empty result or a not-found record.

## Interaction

### Interaction states

All links, search fields, native selects and disclosure summaries have visible keyboard focus.
Interactive rows may receive a quiet border or background change on hover; no status depends on
hover. The name filter changes only the displayed roster list and never creates an identity match.

### Motion

Use short ease-out transitions for link and card hover only. Respect `prefers-reduced-motion` by
removing transforms and smooth scrolling.

### Responsive behavior and accessibility

At narrow widths, cards become one column, the profile index becomes a normal flow panel and
metadata wraps instead of clipping. The page includes a skip link, a Korean document language,
semantic headings/landmarks, labelled search, visible focus and touch targets of at least 44px;
search inputs, selects and primary filter buttons are 48px tall.

## Do / Don't

- Do show the current status beside the item it describes.
- Do keep source and policy context one interaction away from a claim.
- Don't add scores, rankings, inferred affiliations or unsupported asset/vote dashboards.
- Don't turn a provider row, name or review item into a canonical Person control.
- Don't put a small colored label (eyebrow) above every heading, and don't pair each heading with a
  right-aligned gray paragraph. A heading is followed by at most one short line under it.
- Don't add decorative ordinal numbers (01/02/03), italic or colored accent words in headings,
  initial-letter avatars, circular arrow badges, KPI tiles or "where to start" card grids.
- Use Korean public headings and status labels; preserve original source quotations and identifiers only where their exact form matters.
- Don't add reassurance or disclaimer prose ("근거와 출처와 함께…", "없다는 뜻이 아니라…",
  "자동으로 합치지 않습니다", footer promises). Home carries one scope line. A short factual note is
  kept only where a misreading could harm someone, such as witness lists being 출석 요구, not a
  finding of wrongdoing.
- Don't use the KRDS government masthead, identifier, emblem or any government-site styling; this
  is not a government service.
- Don't copy third-party design-system assets (fonts, icons, tokens) without a license that allows it.

## Implementation notes

The visual contract is this file and the semantic CSS variables in `apps/web/app/styles.css`.
The existing Server Component data reads in `apps/web/app/data.ts` remain the read boundary. The
small client-side roster filter receives only serializable `Person` records from the server and
does not call a new API or mutate canonical data. Home and People changes must not introduce a
feeder, schema, dependency or second provenance presentation path.
