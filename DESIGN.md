---
name: Yes Officer
description: Live MCQ polling and class chat, built as a library card catalog.
colors:
  cabinet: "#1f3a5f"
  cabinet-deep: "#172d4a"
  cabinet-hi: "#2c4f7c"
  cabinet-ink: "#e3ebf5"
  cabinet-ink-2: "#b8c8dc"
  blotter: "#e6ebf0"
  blotter-2: "#d9e0e8"
  card: "#fcfcfa"
  paper: "#ffffff"
  ink: "#14223a"
  ink-2: "#3f4f66"
  ink-3: "#56657b"
  line: "#c9d3de"
  line-2: "#dfe5ec"
  rule-red: "#c8102e"
  rule-red-soft: "#f3cbd2"
  rule-blue: "#c4dbef"
  tab-canary: "#ffd84d"
  tab-sky: "#93c4ea"
  tab-pink: "#ffa3c4"
  tab-mint: "#86dbab"
  tab-apricot: "#ffb784"
  tab-lilac: "#cbb9ff"
  ok: "#17703f"
  ok-soft: "#e3f3ea"
  warn: "#8a5a00"
  warn-soft: "#fff4d6"
  danger: "#b0102a"
  danger-soft: "#fde8eb"
  focus: "#1d64d8"
typography:
  display:
    fontFamily: "Atkinson Hyperlegible, system-ui, sans-serif"
    fontSize: "2.5rem"
    fontWeight: 700
    lineHeight: "48px"
  headline:
    fontFamily: "Atkinson Hyperlegible, system-ui, sans-serif"
    fontSize: "1.875rem"
    fontWeight: 700
    lineHeight: "36px"
  title:
    fontFamily: "Atkinson Hyperlegible, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 700
    lineHeight: 1.2
  body:
    fontFamily: "Atkinson Hyperlegible, system-ui, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.5
  body-sm:
    fontFamily: "Atkinson Hyperlegible, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.4
  label:
    fontFamily: "Atkinson Hyperlegible, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 700
    lineHeight: 1.5
  call-number:
    fontFamily: "Courier Prime, ui-monospace, monospace"
    fontSize: "0.9375rem"
    fontWeight: 700
    letterSpacing: "0.08em"
    fontFeature: "tnum"
  count:
    fontFamily: "Courier Prime, ui-monospace, monospace"
    fontSize: "1.25rem"
    fontWeight: 700
    fontFeature: "tnum"
  meta:
    fontFamily: "Courier Prime, ui-monospace, monospace"
    fontSize: "0.8125rem"
    fontWeight: 400
rounded:
  tag: "3px"
  card: "4px"
  control: "6px"
  pill: "50%"
spacing:
  s-1: "4px"
  s-2: "8px"
  s-3: "12px"
  s-4: "16px"
  s-5: "24px"
  s-6: "32px"
  s-7: "48px"
components:
  button-primary:
    backgroundColor: "{colors.cabinet}"
    textColor: "{colors.paper}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "0 16px"
    height: "42px"
  button-primary-hover:
    backgroundColor: "{colors.cabinet-hi}"
  button-secondary:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.cabinet}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "0 16px"
    height: "42px"
  button-danger:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.danger}"
    rounded: "{rounded.control}"
    height: "42px"
  button-danger-hover:
    backgroundColor: "{colors.danger-soft}"
  button-ghost-hover:
    backgroundColor: "{colors.blotter-2}"
  input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
    height: "44px"
  index-card:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "24px 32px 32px"
  option:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.title}"
    padding: "12px 16px"
    height: "60px"
  option-correct:
    backgroundColor: "{colors.ok-soft}"
  option-wrong:
    backgroundColor: "{colors.danger-soft}"
  option-faded:
    textColor: "{colors.ink-3}"
  stamp-ok:
    backgroundColor: "{colors.ok-soft}"
    textColor: "{colors.ok}"
    typography: "{typography.call-number}"
    rounded: "{rounded.card}"
    padding: "6px 12px"
  stamp-closed:
    backgroundColor: "{colors.danger-soft}"
    textColor: "{colors.danger}"
    typography: "{typography.call-number}"
    rounded: "{rounded.card}"
    padding: "6px 12px"
  stamp-muted:
    backgroundColor: "{colors.blotter}"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.card}"
    padding: "6px 12px"
  live-pill:
    backgroundColor: "{colors.rule-red}"
    textColor: "{colors.paper}"
    typography: "{typography.call-number}"
    rounded: "{rounded.card}"
    padding: "3px 10px"
  drawer-card:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.tag}"
    width: "168px"
    height: "92px"
  panel:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "12px 16px"
  rail:
    backgroundColor: "{colors.cabinet}"
    textColor: "{colors.cabinet-ink}"
    width: "236px"
  rail-link-active:
    backgroundColor: "{colors.cabinet-deep}"
    textColor: "{colors.paper}"
    rounded: "{rounded.control}"
  toast:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "16px 16px 12px"
---

# Design System: Yes Officer

## Overview

**Creative North Star: "The Card Catalog"**

Every question is an index card; the live poll is the card pulled out of the drawer. The app is a working library cabinet: a solid cabinet-blue navigation field, a cool blotter-grey desk, and white ruled card stock carrying a red header rule and pale-blue writing lines. The open card leads every live screen; everything around it (insights, chat, the drawer of upcoming cards) steps back one tone so the teacher and the student both read "what is happening right now" first.

The system is dense but calm, built for Operate mode: a teacher on a laptop running a class while talking, a student on a phone tapping an answer before time runs out. Colour works at field scale (the cabinet rail, the blotter ground) and at tab scale (six card-pack colours that identify options A to F). State is carried by form, the way a catalog clerk would mark a card: a solid border for chosen, a dashed one for pending, a double-ruled rubber stamp for accepted or closed, a strike-through for wrong or cancelled.

It refuses the category default of a grey dashboard with indigo bars and soft white cards. Typography is plain and highly legible (Atkinson Hyperlegible); the typewriter face (Courier Prime) is the catalog's own voice and is kept to what a clerk would type: call numbers, timers, counts, letters and stamps.

**Key Characteristics:**
- Ruled index card as the primary container, with a full-width red header rule that drains as time runs out.
- Options A to F wear coloured card-pack tabs and a letter disc; colour never travels without its letter.
- State by form: solid, dashed, double-ruled stamp, strike-through.
- Cabinet-blue rail and blotter ground; no gradients, no glass, no decorative imagery.
- Courier Prime only for typed catalog data; Atkinson Hyperlegible for everything people read.

## Colors

A cool, institutional cabinet-and-paper palette, punctuated by one red rule and six pastel card-pack tabs.

### Primary
- **Cabinet Blue** (cabinet): the navigation rail, the auth side panel, primary buttons, the selected segment, links and the chat author name. Its deep variant (cabinet-deep) marks the current rail item; its high variant (cabinet-hi) is the hover and divider tone inside the rail. Rail text uses the pale cabinet inks (cabinet-ink, cabinet-ink-2).

### Secondary
- **Catalog Red** (rule-red): the index card's header rule, the top rule on toasts, room cards, live banners and drawer cards, the LIVE pill and the ACTIVE status tag, the text caret and the reader's own name in chat. Its soft variant (rule-red-soft) is the drained track behind the header rule.
- **Ruling Blue** (rule-blue): the pale writing lines on card stock only.

### Tertiary
- **Card-Pack Tabs** (tab-canary, tab-sky, tab-pink, tab-mint, tab-apricot, tab-lilac): assigned to options A to F in that fixed order, and reused for insight category chips. Canary also marks the current rail icon, the mobile rail underline, the teacher badge in chat and text selection. Tabs always carry ink text.

### Neutral
- **Blotter** (blotter, blotter-2): the page ground and the ghost-button hover.
- **Card Stock** (card): index cards, drawer cards, room cards, toasts. Slightly warm against the cool ground.
- **Paper** (paper): panels, fields, option rows, list cards.
- **Ink** (ink, ink-2, ink-3): primary text, secondary text and call numbers, tertiary text and placeholders. Ink-3 is the lightest text tone permitted on card or paper.
- **Lines** (line, line-2): field and panel borders, and inner dividers.

### Status
- **Verified Green** (ok, ok-soft), **Danger Red** (danger, danger-soft), **Warn Amber** (warn, warn-soft): correct/accepted, wrong/closed/destructive, caution. Always paired with a word, an icon or a form change.
- **Focus Blue** (focus): the 3px focus ring, and the focused field border.

### Named Rules
**The One Red Rule.** Catalog red marks time, liveness and the card's header edge. It is not a general accent; never use it for buttons or emphasis text. Destructive actions use danger, not rule-red.

**The Letter-With-Colour Rule.** A tab colour never identifies an option on its own. Every tab carries its letter, and every option row repeats the letter in a disc.

**The Brand Tile Rule.** The maroon (#601800) "yes OFFICER" logo is used exactly as supplied, as the shell brand mark and the app icon. Maroon belongs to the logo tile only; it is not a UI colour.

## Typography

**Body Font:** Atkinson Hyperlegible (with system-ui, sans-serif), weights 400 and 700.
**Label/Mono Font:** Courier Prime (with ui-monospace, monospace), weights 400 and 700, tabular numerals.

**Character:** A legibility face built for low-vision readers does all the reading work; a typewriter face does the clerk's typing. The pairing makes the screen read as a catalog without making any sentence harder to read.

### Hierarchy
- **Display** (700, 2.5rem, 48px leading): the live-console question prompt at 1200px and wider.
- **Headline** (700, 1.875rem, 36px leading): question prompts on index cards (max 34ch) and page titles (1.2 leading). Drops to 1.5rem/30px on compact cards and under 640px.
- **Title** (700, 1.25rem, 1.2): section titles, panel-adjacent headings, room-card names, option labels (1.3 leading; 1.5rem in the wide console).
- **Body** (400, 1.0625rem, 1.5): default text. Small body (0.9375rem) for chat, insights, alerts, toasts; extra-small (0.8125rem) for hints.
- **Label** (700, 0.9375rem): buttons, field labels, rail links, segmented controls.
- **Call number** (Courier Prime 700, 0.9375rem, 0.08em tracking): "Q 1 OF 3", time left, stamps (uppercase), the LIVE pill.
- **Count** (Courier Prime 700, 1.25rem, tabular): live answer counts on options and the console answered count.
- **Meta** (Courier Prime 400, 0.8125rem): version numbers, online counts, timestamps, save state.

### Named Rules
**The Typed-Data Rule.** Courier Prime is for what a clerk types onto a card: call numbers, timers, counts, letters, stamps, status tags and metadata. Prompts, headings, body text, buttons and field labels are always Atkinson Hyperlegible.

**The Leading-Is-Ruling Rule.** A card prompt's line-height equals the card's rule pitch (36px, 30px compact, 48px wide console), so each line of the prompt sits on a ruled line.

## Layout

The app shell is a two-column grid: a 236px sticky cabinet rail and a fluid main column padded 24px top, 32px sides, 48px bottom. Under 860px the rail becomes a horizontal sticky bar (logo tile only, short link labels, icon-only sign-out, canary underline on the current item) and main padding drops to 16px.

Live and room screens use a main column plus a 360px side column (insights above chat on the teacher console; chat beside the card in rooms), with 16 to 24px gaps. The console's side column is sticky. Under 1100px these stack to one column; under 640px the student room swaps question and chat with a full-width segmented control.

Options sit in a 2-column grid (24px row gap to clear the tabs, 16px column gap), one column under 640px. Room browse cards use an auto-fill grid of 260px minimum.

Spacing follows a 4px-based scale (4, 8, 12, 16, 24, 32, 48). Touch targets: buttons 42px (34px small, 38px icon), fields 44px, options 60px (72px and up in the console).

## Elevation & Depth

Hybrid: paper surfaces (panels, fields, list cards) are flat with a 1px line border; card stock (index cards, drawer cards, room cards, toasts, dialogs) lifts off the blotter with a crisp 1px base edge plus a soft, downward-offset shadow, like a card resting on a desk. There are no hard offset shadows, no glows and no blur.

### Shadow Vocabulary
- **Lift** (`box-shadow: 0 1px 0 rgba(20, 34, 58, 0.14), 0 12px 28px -16px rgba(20, 34, 58, 0.45)`): index cards, toasts, live banner, dialogs.
- **Lift Small** (`box-shadow: 0 1px 0 rgba(20, 34, 58, 0.12), 0 4px 10px -6px rgba(20, 34, 58, 0.35)`): drawer cards, room cards, chosen options and option hover.

### Named Rules
**The Card-Stock-Lifts Rule.** Only card stock casts a shadow. Paper surfaces stay flat and bordered. Live focus is shown by tone: side panels in the console drop to a softer ground (#f5f7f9) and lighter border while the open card keeps full lift.

## Shapes

Corners are small and consistent: 3px for tags, chips and drawer cards; 4px for card stock and stamps; 6px for controls, panels and fields; letter discs and spinners are circles. The card-pack tab is the one distinctive silhouette: a 19px-tall tab with 5px top corners that rises from the option's top-left edge, and the option body squares its top-left corner (0 6px 6px 6px) to meet it. Card rules run full bleed across the card, and top rules on containers run full width along the top edge. Stamps are rotated -3deg; the auth sample card sits at -1.2deg. Nothing else is rotated.

## Components

### Buttons
Plain, square-shouldered and confident.
- **Shape:** gently rounded (6px), 42px tall, 16px side padding, label type.
- **Secondary (default):** paper fill, 1px cabinet border, cabinet text; hover tints to #eef3f9.
- **Primary:** cabinet fill, white text; hover to cabinet-hi.
- **Danger:** danger border and text, hover to danger-soft.
- **Ghost:** no border or fill; hover to blotter-2.
- **States:** active presses down 1px; disabled at 50% opacity; focus is the global 3px focus-blue outline at 2px offset.

### Segmented control
A paper strip with a 1px line border and 2px inset; the pressed segment fills cabinet with white text. Used for insight scope and the mobile question/chat switch.

### Cards / Containers
- **Index card:** card stock, 4px corners, Lift, 24px/32px padding (16px under 640px). Ruled with ruling-blue 1px lines every `--pitch` (36px; 30px compact or mobile; 48px wide console), starting at `--ruled-from` so each rule falls about 4px under a prompt baseline. The draft editor keeps the stock but drops the ruling behind its controls.
- **Panel:** paper, 1px line border, 6px corners; a head row (12px/16px, line-2 divider, medium title) and a scrolling body.
- **List card / room card:** list cards are bordered paper with 64px rows; room cards are card stock with a 3px red top rule, Lift Small, and a canary (or red when live) tab label.

### Inputs / Fields
- **Style:** paper, 1px line border, 6px corners, 44px minimum, label above in label type, hint in ink-3 extra-small.
- **Focus:** border turns focus blue with a 2px 30% focus-blue outline.
- **Error:** danger text below the field; form-level errors in a danger-soft alert.

### Navigation
The cabinet rail: logo tile and wordmark, then rail links in label type (cabinet-ink-2; hover cabinet-hi with white; current page cabinet-deep with white text and a canary icon). A red Courier LIVE tag sits on the room link during a poll. The user block sits at the foot above a cabinet-hi divider.

### Index Card (signature)
Call number row ("Q 3 OF 5" left, "04:38 LEFT" right, Courier call-number type), then a 3px full-bleed header rule: a rule-red-soft track with a rule-red bar that scales from the left as remaining time / limit, so time drains one way, then the prompt in headline type on the ruling.

### Option Tabs (signature)
Paper row, 1px line border, a coloured card-pack tab with the letter, a 32px letter disc (2px ink ring), the label, and optionally a live count and a 5px meter in the tab colour along the bottom.
- **Chosen:** 2px solid ink border, Lift Small, disc fills ink with white letter.
- **Pending:** 2px dashed ink-2 border.
- **Faded:** line-2 border, ink-3 text and disc, tab at 55% opacity.
- **Correct:** 2px ok border, ok-soft fill, plus a check icon and the word "Correct".
- **Wrong:** 2px danger border, danger-soft fill, label struck through, plus an X icon and "Your answer".

### Stamps
Courier uppercase, 0.08em tracking, 3px double border in currentColor, 4px corners, rotated -3deg. Ok (green on ok-soft: Accepted, Correct), Pending (2px dashed ink-2: Sending), Closed (danger on danger-soft: Incorrect, Time's up, errors), Muted (ink-2 on blotter: Not answered). Status tags follow the same logic at tag size: DRAFT dashed, ACTIVE red fill, COMPLETED green outline, CANCELLED struck.

### Drawer Strip (signature)
A horizontal row of identical 168x92px mini cards (card stock, Lift Small, 3px red top rule, Courier "Q1" and a two-line clamped prompt). The open card lifts 14px with a 2px cabinet outline; done cards drop to 60% with a struck call number.

### Chat and Insights
Chat lines are small body text with a bold cabinet author name; the reader's own name is rule-red; teachers get a canary Courier "teacher" badge. The empty state says chat is not saved. Insights pair a tab-coloured category chip with a dashed "AI" label (inference) and Courier metadata; verified results carry a solid green "Verified answers" label instead, so inference and fact never share a style.

### Toasts
Card stock with Lift, 4px corners and a 4px top rule drawn as a background layer (rule-red; ok for success), bottom-right, 380px wide (full width with 16px insets on mobile).

### Motion
- **Card pull** (0.6s, ease-out cubic-bezier(0.16, 1, 0.3, 1)): a new question card rises 28px from a -0.6deg tilt.
- **Stamp in** (0.35s ease-out): the accepted stamp lands from 1.6x scale.
- **Drain** (0.25s linear per tick): the header rule's scaleX.
- **Meter** (0.5s ease-out), toast in (0.45s), button/option press (0.15s), drawer lift (0.4s), LIVE dot blink (1.6s).
- **Reduced motion:** under prefers-reduced-motion every animation and transition collapses to 0.01ms with one iteration; state still changes, nothing moves.

## Do's and Don'ts

### Do:
- **Do** put every question on an index card: call number, red header rule, prompt on the ruling, with prompt line-height equal to `--pitch`.
- **Do** draw top red rules as full-width top-edge layers (a background gradient on toasts, banners and room cards; the drained bar on index cards).
- **Do** pair every tab colour with its letter, and every correct/wrong state with an icon and a word as well as colour.
- **Do** show state by form: solid for chosen, dashed for pending, double-ruled stamp for accepted or closed, strike-through for wrong, done or cancelled.
- **Do** keep Courier Prime to call numbers, timers, counts, letters, stamps, tags and metadata.
- **Do** label AI insights with the dashed AI label and verified results with the solid Verified label.
- **Do** treat chat as ephemeral in the UI: no history loaders, and say plainly that it is not saved.
- **Do** honour the reduced-motion collapse for any new animation.

### Don't:
- **Don't** use side stripes (a coloured left or right border) on cards, alerts, list rows or messages.
- **Don't** use Courier Prime for prompts, headings, body copy, buttons or field labels.
- **Don't** signal correctness, acceptance or option identity by colour alone.
- **Don't** use catalog red as a general accent or for destructive buttons.
- **Don't** recolour, redraw or restyle the supplied maroon logo, or borrow its maroon for UI.
- **Don't** add hard offset shadows, glows, gradients or glass; only card stock lifts.
- **Don't** add uppercase tracked kicker labels above headings.
