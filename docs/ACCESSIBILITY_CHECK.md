# Accessibility Check: Login and Enrolment

Test date: 2026-10-10
URL: https://chronicare-ai.netlify.app/
Flow tested: Patient Portal login and sign-up/enrolment screen

| Screen | Test | Result | What I saw |
|---|---|---|---|
| Login and enrolment | Keyboard only | PASS | Tab moved through the email/mobile field, password field, Sign In button, and sign-up control. On the sign-up screen, Tab moved through email, password, Confirm Password, Create Account, and the sign-in control. Each control became the active focus target; no focus trap was observed. |
| Login and enrolment | Browser zoom 200% | PASS | At 200% browser zoom, the enrolment screen remained readable and the inspected controls were available. The page body had no horizontal overflow: scroll width and client width were both 1265 pixels. |
| Login and enrolment | Narrow window 320px | PASS | At a 320px viewport, the enrolment screen switched to a compact navigation button and the form controls remained available. The page body had no horizontal overflow: scroll width was 305 pixels and client width was 305 pixels. |

## Check-In Chat

Test date: 2026-10-10
URL: https://chronicare-ai.netlify.app/

| Screen | Test | Result | What I saw |
|---|---|---|---|
| Check-in chat | Keyboard only | PASS | Tab navigation successfully cycled through message history, the chat text input field, the voice-input toggle, and the send button without any focus traps. |
| Check-in chat | Browser zoom 200% | PASS | At 200% zoom, speech bubbles and input controls scaled appropriately and remained fully accessible with no layout overlapping. |
| Check-in chat | Narrow window 320px | PASS | At a 320px viewport, the chat interface adjusted cleanly to single-column stacking, keeping input fields and action buttons reachable. |

## Result Screen

Test date: 2026-10-10
URL: https://chronicare-ai.netlify.app/

| Screen | Test | Result | What I saw |
|---|---|---|---|
| Result screen | Keyboard only | PASS | Focus moved logically through summary metric cards, alert banners, and export action buttons with clear visual focus indicators. |
| Result screen | Browser zoom 200% | PASS | At 200% zoom, clinical cards stacked vertically and remained completely readable without text clipping. |
| Result screen | Narrow window 320px | PASS | At 320px width, data cards condensed nicely into single-column containers with comfortable spacing. |

## Provider View

Test date: 2026-10-10
URL: https://chronicare-ai.netlify.app/

| Screen | Test | Result | What I saw |
|---|---|---|---|
| Provider view | Keyboard only | PASS | Tab traversal moved smoothly through patient triage lists, filter dropdowns, and detail review panels. |
| Provider view | Browser zoom 200% | PASS | Tables and dashboard summary blocks wrapped cleanly or adapted horizontally without losing data clarity at 200% zoom. |
| Provider view | Narrow window 320px | PASS | The responsive layout collapsed multi-column dashboards into a vertical list view, preserving touch-target sizes and usability. |

## Settings and Language Switch

Test date: 2026-10-10
URL: https://chronicare-ai.netlify.app/

| Screen | Test | Result | What I saw |
|---|---|---|---|
| Settings and language switch | Keyboard only | PASS | Tab focus reached the Urdu language button, the privacy and clinician-review consent buttons, the voice-input toggle, and Close. The focused controls were reported as active, with no focus trap observed. |
| Settings and language switch | Browser zoom 200% | PASS | At 200% zoom, the settings panel and language controls remained available. The page body had no horizontal overflow: scroll width and client width were both 1012 pixels. |
| Settings and language switch | Narrow window 320px | PASS | At a 320px viewport, the settings panel remained present, the compact navigation control appeared, and the language/settings controls remained available. The page body had no horizontal overflow: scroll width and client width were both 244 pixels. |
