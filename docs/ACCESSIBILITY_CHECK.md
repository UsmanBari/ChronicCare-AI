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
| Check-in chat | Keyboard only | NOT DONE | The chat screen could not be reached. The public “Launch Patient Portal Demo” control left the portal-selection screen unchanged, and the live login rejected the non-empty test credentials with `Invalid credentials. Please check your email and password.` |
| Check-in chat | Browser zoom 200% | NOT DONE | The chat screen could not be reached because authentication blocked entry. No chat-screen zoom observation was recorded. |
| Check-in chat | Narrow window 320px | NOT DONE | The chat screen could not be reached because authentication blocked entry. No chat-screen narrow-viewport observation was recorded. |

## Result Screen

Test date: 2026-10-10
URL: https://chronicare-ai.netlify.app/

| Screen | Test | Result | What I saw |
|---|---|---|---|
| Result screen | Keyboard only | NOT DONE | The result screen could not be reached. The public patient-demo entry did not leave the portal-selection screen, and the live login rejected the non-empty test credentials with `Invalid credentials. Please check your email and password.` |
| Result screen | Browser zoom 200% | NOT DONE | Authentication blocked entry to the result screen, so no zoom observation was recorded. |
| Result screen | Narrow window 320px | NOT DONE | Authentication blocked entry to the result screen, so no narrow-viewport observation was recorded. |
