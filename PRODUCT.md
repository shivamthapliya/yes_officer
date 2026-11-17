# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

React + JavaScript (Vite) frontend, as required by `docs/requirements.md`. FastAPI backend (`backend/`), PostgreSQL, Redis, Celery. The frontend reads every backend URL from one central config (`VITE_API_BASE_URL`), never hardcoded.

## Users

- **Teachers** running a remote (online) class from a laptop/desktop. During a live poll they step through questions one at a time, watch answers arrive, read live class chat, and glance at AI insights about doubts and confusion — all at once, while also talking to the class.
- **Students** attending that remote class from their own device, often a phone. They join their teacher's room, chat, answer the open question before time runs out, see results the moment the poll ends, and later review their own answers.

## Product Purpose

"Yes Officer" (the user-facing product name, general education audience) is a real-time quiz and live-polling platform. Each teacher has exactly one permanent room; polls run inside it over time. Success: the teacher can run a poll and understand the class's real state (answers plus what chat reveals) without leaving one screen, and students get instant, fair feedback.

## Positioning

Official MCQ answers and AI chat analysis are deliberately separate pipelines: answers are verified facts (first valid answer wins, server receipt time), while AI insights from chat (common doubts, confusion, misconceptions, uncounted "I think it's B" responses, student questions) are clearly labeled inferences that never alter results.

## Operating Context

- Remote class: teacher shares voice/video elsewhere; this app is the poll + chat surface.
- Live poll flow: draft → start → teacher advances questions → ends (or deadline auto-ends, max 5 min per poll) → results shown to everyone immediately, with the first correct student announced in a toast. A teacher may cancel instead (no results kept).
- Chat is ephemeral (YouTube-Live style): no history, a reload starts empty, at most 200 messages kept in the browser.
- AI insights update in real time; the panel holds each displayed version for at least 6 seconds and ignores stale versions.

## Capabilities and Constraints

- Roles: Teacher, Student. One room per teacher (auto-provisioned, renamable). Students browse and join rooms.
- MCQ only: 2–6 options, exactly one correct. Time limit 10–300 s per poll. No scoring, totals, or percentages per student.
- Per-question results: option distribution, correct option, answered count, participant count, first correct student.
- Student history: per poll, each question with their answer, the correct answer, and correct/incorrect.
- Auth via HTTP-only cookies; WebSocket at `/api/ws/rooms/{id}`.

## Brand Commitments

- Official logo (supplied by the product owner, 2026-11-17): white "yes" with a long slanted y descender over condensed "OFFICER", on a maroon `#601800` square. Source file: `frontend/src/assets/brand/yes-officer-logo.png`. Use it as supplied, never redrawn or recoloured; square derivatives are padded on the same maroon ground. It is the app icon (favicon, touch icon) and the brand mark in the app shell.

## Evidence on Hand

The logo above is the only brand asset. No testimonials or real class data exist. Do not fabricate any.

## Product Principles

1. The live moment comes first: during a poll, the teacher's screen answers "what is happening right now?" at a glance.
2. Facts and inferences never blur: verified answer data and AI observations are visually and verbally distinct.
3. Fairness is visible: students see clearly whether their answer was accepted, and when time runs out.
4. Phones are first-class for students; the teacher dashboard is desktop-first.

## Accessibility & Inclusion

Target WCAG 2.2 AA. Live updates (timer, new question, results) must be announced to assistive tech without being noisy; never rely on color alone for correct/incorrect.
