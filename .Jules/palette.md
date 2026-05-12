## 2026-05-12 - [CSP Enforcement on Inline Scripts]
**Learning:** This application has a strict Content Security Policy (`default-src 'self'`) that blocks inline JavaScript event handlers (like `onclick`) and inline `<script>` tags. UX enhancements requiring interactivity must use external JS files and `addEventListener` to comply with these security headers.
**Action:** Always check for `Content-Security-Policy` headers before implementing interactivity. Favor external scripts over inline handlers to ensure features work in locked-down environments.
