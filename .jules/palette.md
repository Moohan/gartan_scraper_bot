## 2026-04-06 - Enhancing Real-time Dashboard Accessibility
**Learning:** For monitoring dashboards that auto-refresh, using `aria-live="polite"` on key status indicators and summary statistics provides a better experience for screen reader users by announcing changes without aggressive interruption. Adding a visual pulsating indicator (with `aria-hidden="true"`) helps sighted users quickly identify that the data is live and actively updating.
**Action:** Always pair auto-refreshing UI with `aria-live` regions and a "Live" visual state to provide multi-modal feedback about the data's freshness.

## 2026-04-06 - Respecting Reduced Motion Preferences
**Learning:** Animations like pulsating indicators and interactive hover transforms can be distracting or problematic for users with motion sensitivities. Using the `prefers-reduced-motion: reduce` media query allows us to provide the same functional feedback (e.g., using a static box-shadow instead of a pulse animation) while respecting user preferences.
**Action:** Always wrap non-essential animations and transforms in `prefers-reduced-motion` media queries to ensure the interface remains accessible to all users.
