---
version: 1
slug: "frontend-src"
primary_target: "frontend/src"
related_targets: []
---

# Surface brief: Yes Officer web app (teacher + student)

Scope: the whole React web app in `frontend/` — auth, teacher room/drafts/live console/results/history, student rooms/live room/history/review. Visitor mode: **Operate**. Build path: code-led (no image generation).

Audience & job: teachers running a remote class on a laptop (desktop-first); students on their own device, often a phone (mobile-first for the live room). Task: run or take a live MCQ poll while chatting; see verified results instantly; review later.

Constraints: AA contrast; correctness never by colour alone; chat is ephemeral (max 200, no fetch); insights panel holds each version ≥6 s and ignores stale versions; every backend URL from `src/config/api.js`.

## Direction contract

THESIS: Every question is an index card; the live poll is the card pulled out of the drawer. Refuses the category default of a grey dashboard with indigo bars and soft white cards.

OWN-WORLD: Solid cabinet-blue (#1F3A5F) navigation field; cool blotter-grey ground; white ruled card stock with a red header rule and pale-blue rules; option A–F wear coloured card-pack tabs (canary, sky, pink, mint, apricot, lilac) plus a letter disc; Atkinson Hyperlegible for UI, Courier Prime for call numbers, timers and counts. State by form: accepted solid stamp, pending dashed, closed struck.

STORY: The teacher sees at a glance which card is open, how many answered, what chat and AI say, and advances or ends with one button. Students see one big card, tap an option, get an unmistakable "accepted" stamp, then the result.

FIRST VIEWPORT: Teacher live console — left cabinet-blue rail (brand, My room, Drafts, History); top bar with LIVE timer pill, poll title, answered count, Cancel / Next / End; centre: large ruled question card (call number "Q 3 OF 5", countdown draining along the red rule, 2×2 option tabs with live counts); below: drawer strip of identical mini cards, open one lifted; right column: AI insights panel above class chat.

FORM: Card Catalog, position 4 of my ordered list (assigned by the roll). seed:2d85b6753a859a78
Raises: state by form (from Emission Line Rail); fixed-scale card strip (Botanical Folio); live focus dims the rest one step (Streaming Wall); colour at field scale (Guide Map); time drains one way along the red rule (Labanotation).
Signature move: the open question card with its draining red rule and coloured option tabs; the drawer strip.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Unresolved

- None blocking. Room browse and drafts reuse the card language at rest.
