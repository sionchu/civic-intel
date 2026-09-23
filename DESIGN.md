# Civic Intel Design System

## Design intent

Civic Intel is a Korean-first public-record directory. The interface should help a reader move
from a person to the record behind a claim without turning a source into a verdict, score or
social feed. The visual tone is quiet, editorial, precise and content-first.

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
- Explain what is visible, where it comes from and how it was checked without leading with
  implementation vocabulary.

External design references may inform this grammar, but they do not override product behavior,
evidence rules, accessibility or existing component conventions. No external brand assets, copy,
fonts, icons, screenshots or proprietary tokens are part of this system.

## Foundations

### Color roles and semantic tokens

The light theme uses these roles in `apps/web/app/styles.css`:

- `--color-canvas`: warm page background.
- `--color-surface` / `--color-surface-muted`: primary and secondary panels.
- `--color-ink` / `--color-ink-muted`: primary and supporting text.
- `--color-line` / `--color-line-strong`: quiet and emphasized borders.
- `--color-accent` / `--color-accent-soft`: navigation, links and positive traceability cues.
- `--color-warning` / `--color-warning-soft`: claims, review and partial states.
- `--color-danger` / `--color-danger-soft`: refute, conflict and service-failure states.
- `--color-focus`: keyboard focus ring.

Status colors are semantic only: green is not a confidence score, amber is not a risk score and
red is not a wrongdoing claim. `UNKNOWN` is a neutral unresolved evidence state, not an error;
transport failure and source conflict use distinct feedback treatment and language.

### Typography

Use a system sans stack with Korean-safe fallbacks for body text, controls and dense evidence
metadata. Use a Korean-safe serif fallback stack for display headings and names. Body copy stays
between 15px and 18px with generous line height. Uppercase tracking is reserved for small route
labels, not primary content.

### Spacing scale

Use a 4px base with recurring values of 8, 12, 16, 24, 32 and 48px. Dense evidence rows use
8–12px gaps; page regions use 32–64px. Avoid new arbitrary spacing values unless a content-driven
breakpoint requires one.

### Layout and containers

The content container is capped at 1180px with fluid 20–48px gutters. Home uses a two-column
introduction that collapses to one column. People uses a readable directory column with flat
editorial rows and one mobile column. Profile pages keep their narrow index beside a readable
content column and reflow below 820px. Long Korean values and identifiers wrap instead of clip.

### Borders, radii, shadows and surfaces

The default surface uses a 1px border and no shadow. Rounded corners are limited to controls,
groups, avatars and feedback panels. Functional elevation may be used sparingly for an explicit
interactive surface. Avoid glass effects, heavy gradients and decorative depth that could make
source status feel more authoritative than the evidence.

## Components

### Records and panels

Roster records are flat clickable rows with canonical name, evidenced role, available profile
fields, evidence/as-of metadata and a clear profile link. Profile claims and sources are separate
panels. Public review displays remain read-only. The explicitly enabled private admin workspace uses
selected-record review, before/after previews, final confirmation and server-acknowledged receipts.
Operational IDs and full audit details remain expandable; mutation success is never optimistic.

### Reviewed portraits

Portraits are an optional Person-detail presentation asset only. A portrait is displayed only
after an individual file-level rights review and an exact binding to a resolved canonical Person
ID; the visible creator, source-file and license links remain beside the image. The local copy
keeps the reviewed aspect ratio without an additional crop and falls back to the existing
initials/CI stamp when the review is absent or withdrawn. Portrait coverage has no semantic
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

Use the existing domain labels verbatim: `FACT`, `CLAIM`, `INFERENCE`, `HYPOTHESIS`, `UNKNOWN`,
`AVAILABLE`, `PARTIAL`, `RESOLVED`, `REVIEW_REQUIRED`, `HARD_CONFLICT` and `SOURCE CONFLICT`.
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
semantic headings/landmarks, labelled search, visible focus and touch targets of at least 44px.

## Do / Don't

- Do show the current status beside the item it describes.
- Do keep source and policy context one interaction away from a claim.
- Don't add scores, rankings, inferred affiliations or unsupported asset/vote dashboards.
- Don't turn a provider row, name or review item into a canonical Person control.

## Implementation notes

The visual contract is this file and the semantic CSS variables in `apps/web/app/styles.css`.
The existing Server Component data reads in `apps/web/app/data.ts` remain the read boundary. The
small client-side roster filter receives only serializable `Person` records from the server and
does not call a new API or mutate canonical data. Home and People changes must not introduce a
feeder, schema, dependency or second provenance presentation path.
