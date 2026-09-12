# Civic Intel Design System

## Design intent

Civic Intel is a Korean-first, read-only Evidence Directory for people whose public roles and
claims can be followed back to published evidence. The site should feel calm and inspectable:
the interface helps a reader move from a resolved identity to an evidence trace without making
the interface look like a verdict, ranking or social feed.

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

## Foundations

### Color roles and semantic tokens

The light theme uses these roles in `apps/web/app/styles.css`:

- `--color-canvas`: warm page background.
- `--color-surface` / `--color-surface-muted`: primary and secondary panels.
- `--color-ink` / `--color-ink-muted`: primary and supporting text.
- `--color-line` / `--color-line-strong`: quiet and emphasized borders.
- `--color-accent` / `--color-accent-soft`: navigation, links and positive traceability cues.
- `--color-warning` / `--color-warning-soft`: claims, review and partial states.
- `--color-danger` / `--color-danger-soft`: unknown, refute and conflict states.
- `--color-focus`: keyboard focus ring.

Status colors are semantic only: green is not a confidence score, amber is not a risk score and
red is not a wrongdoing claim.

### Typography

Use the system sans stack for controls, labels and dense evidence metadata. Use a Korean-safe
serif fallback stack for display headings and section names. Display headings use a compact,
high-contrast scale; body copy stays between 15px and 18px with generous line height. Uppercase
tracking is reserved for small English kicker labels.

### Spacing scale

Use a 4px base with recurring values of 8, 12, 16, 24, 32 and 48px. Dense evidence rows use
8–12px gaps; page regions use 32–64px. Avoid new arbitrary spacing values unless a content-driven
breakpoint requires one.

### Layout and containers

The content container is capped at 1180px with fluid 20–48px gutters. The roster uses a
responsive three-column card grid; profile pages use a narrow sticky index beside a readable
content column and reflow to one column below 820px. Long identifiers wrap inside audit details.

### Borders, radii, shadows and surfaces

Surfaces use a 1px border, 12–20px radii and a restrained shadow only for primary interactive
cards. Status pills are fully rounded. Avoid glass effects, heavy gradients and decorative
depth that could make source status feel more authoritative than the evidence.

## Components

### Cards and panels

Roster cards are clickable whole-surface links with a visible resolved status, person name and
one action phrase. Profile claims and sources are separate panels. Review cards remain visibly
read-only and keep operational IDs in expandable audit details.

### Navigation

The global header exposes the public directory only. Profile-local navigation is an anchor list
of the existing projection sections. The internal review route is not advertised in public
navigation.

### Tables and data-dense UI

Evidence is presented as stacked readable rows rather than a wide table. Source titles and policy
summaries are visible; UUIDs, hashes and snapshot references stay behind `details` disclosure.

### Status and feedback

Use the existing domain labels verbatim: `FACT`, `CLAIM`, `INFERENCE`, `HYPOTHESIS`, `UNKNOWN`,
`AVAILABLE`, `PARTIAL`, `RESOLVED`, `REVIEW_REQUIRED`, `HARD_CONFLICT` and `SOURCE CONFLICT`.
Empty states explain what is absent without implying a negative fact.

## Interaction

### Interaction states

All links, search fields and disclosure summaries have visible keyboard focus. Clickable cards
lift by a small amount on hover; no status depends on hover. The name filter changes only the
displayed roster list and never creates an identity match.

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

The visual SSOT is this file and the semantic CSS variables in `apps/web/app/styles.css`. The
existing Server Component data reads in `apps/web/app/data.ts` remain the read boundary. The
small client-side roster filter receives only serializable `Person` records from the server and
does not call a new API or mutate canonical data.
