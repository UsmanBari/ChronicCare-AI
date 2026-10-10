# Accessibility Check: Login and Enrolment

Test date: 2026-10-10  
URL: https://chronicare-ai.netlify.app/  
Flow tested: Patient Portal login and sign-up/enrolment screen

| Screen | Test | Result | What I saw |
|---|---|---|---|
| Login and enrolment | Keyboard only | PASS | Tab moved through the email/mobile field, password field, Sign In button, and sign-up control. On the sign-up screen, Tab moved through email, password, Confirm Password, Create Account, and the sign-in control. Each control became the active focus target; no focus trap was observed. |
| Login and enrolment | Browser zoom 200% | PASS | At 200% browser zoom, the enrolment screen remained readable and the inspected controls were available. The page body had no horizontal overflow: scroll width and client width were both 1265 pixels. |
| Login and enrolment | Narrow window 320px | PASS | At a 320px viewport, the enrolment screen switched to a compact navigation button and the form controls remained available. The page body had no horizontal overflow: scroll width was 305 pixels and client width was 305 pixels. |
