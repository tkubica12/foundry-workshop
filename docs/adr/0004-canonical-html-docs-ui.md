# 0004. Use the canonical HTML-docs document runtime

- **Status:** Accepted
- **Date:** 2026-09-17
- **Deciders:** Workshop owner

The canonical-runtime decision remains accepted. The publication scope retaining
all seven decks is superseded by [ADR 0005](0005-labs-first-publication.md), after
the workshop owner changed the active content priority to a labs-first sequence
on 2026-09-18. The original rationale below is retained.

## Context

The workshop owner requested a rewrite of the UI documentation using the latest
installed `html-docs` skill, followed by rendered document review and a guided
manual rehearsal. The existing local material already contains reviewed content
and evidence gates. A visual migration must not silently change lab operations,
release decisions or the distinction between local and native readiness.

## Decision drivers

- Use one reading document with concise presentation surfaces where the narrative
  is shared, rather than maintaining duplicate long and short explanations.
- Preserve links, exercise state, dated sources and honest access prerequisites.
- Keep the runtime local, framework-free and readable without JavaScript.
- Make upstream layout and behavior reusable without per-page runtime patches.
- Support exact-text annotations against editable HTML in Document Review.

## Options considered

### Option A - Reskin the previous workshop runtime

This would preserve its selectors and shared theme storage, but only imitate the
requested skill. Its navigation and disclosure contracts would continue to diverge
from the canonical runtime.

### Option B - Vendor the skill and migrate the document structure

Copy the installed runtime under `docs/assets/html-docs/`, preserve its MIT
license and canonical inline head blocks, and author the corresponding article
and deck structures. Keep domain-specific forms and worksheets in separate,
token-based stylesheets. This requires deliberate migration of browser tests.

### Option C - Replace the workshop with one large article

This would minimize navigation, but mix operating instructions, interactive
worksheets and seven sessions into a document too large to present or read.
It would also obscure the different readiness boundaries.

## Decision

Choose Option B. Guides with a shared reading/presentation narrative use article
cards with concise authored slide surfaces. The interactive passport and session
index remain reading-first. Keep the seven existing speaker-first decks as
separate presentations: they follow the live agenda rather than the fuller
reference-guide structure.

Use blue as the default accent. The owner's explicit request for the latest
skill takes precedence for these migrated documents over the older blue-only
UI rule: retain the canonical reader-selectable orange and green alternatives,
one accent family at a time, without changing tokens. Theme, accent and animation
preferences are per document, not the old cross-document theme key. This does
not change passport data storage or import/export semantics.

Keep existing external anchors as aliases when a canonical chapter or card needs
a new ID. Do not put clickable reference links inside presentation surfaces;
keep accessible links in reading/navigation areas and readable paths on slides.
Do not load both presentation runtimes on a migrated document.

The accessibility companion `document-navigation.css` supplies a screen-only,
no-JavaScript narrow-screen deck reading fallback. Independent review reproduced
horizontal panning from the canonical fixed 1,280px stage at 390px without the
runtime. This repository-wide fallback reflows static slides; it does not change
the canonical files, the live presentation stage, palette or print geometry.

## Consequences

The same reference supports live explanation and deeper reading. A reader can
expand cards, open named sections, change appearance or switch to Slides without
loading external assets. Appearance preferences no longer propagate between
independent documents. Old theme preferences do not override the new defaults.

The repository vendors the selected skill version instead of following an
automatically updating local installation. Later updates require an explicit
asset comparison, head synchronization and regression run. MIT notices travel
with exported files. A standalone document includes its runtime and media, not
the other workshop pages linked from it.

The migration does not provision seats, run models, resolve platform contracts
or qualify native demonstrations. Existing deployment decisions in ADRs 0002
and 0003 remain unchanged.

## Assumptions and revisit triggers

- Modern Chromium-compatible browsers remain the presentation target.
- The existing speaker-first decks retain a different narrative from references;
  merge a deck only when its narrative genuinely becomes the same.
- Revisit domain CSS if the canonical runtime gains equivalent form/worksheet
  components; do not carry duplicate generic styles indefinitely.
- Revisit migration if a future runtime loses stable deep links, no-JavaScript
  reading, accessible controls or offline execution.
- A native rehearsal still requires separately authorized access and completed
  environment prerequisites.

## Validation

Use `node docs\assets\html-docs\sync-head.js --check` on source files, then
`node docs\assets\html-docs\validate.js <document>` at laptop and projector
sizes. The validator traverses all six appearance combinations, slides,
fragments, focus, offline loading and no-JavaScript text parity.

The repository browser collection checks entry-point navigation, persistent
document-scoped preferences, legacy anchors, responsive layouts, actual
fullscreen transitions, passport state and printed pilot answers. Review evidence
and actual run outcomes belong in `teacher/VALIDATION.md`; those results certify
only the local UI path, not the workshop's cloud execution.
