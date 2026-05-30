This article overrides its own presentation two ways at once, and the order
they load in matters.

===The two channels===

In `meta.yaml`, the single `styles:` key splits automatically by key type:

- **String keys** (like `p`, `h3`) become inline rules injected into a
  `<style>` block in the page head. Bare tag names are auto-scoped to
  `section TAG`, so the `p` rule here is really `section p`.
- **Integer keys** (`1`, `2`, …) point to external CSS files inside this
  article folder, linked in ascending order.

===Load order===

The cascade is: `common_template.css` &rarr; external CSS (integer-key order)
&rarr; inline `<style>`. So the inline channel always gets the last word, which
makes it ideal for tiny per-page tweaks.

> This block quote is styled by `custom.css` (the external channel) — a left
> rule and a tinted background — which the inline channel cannot express
> because it forbids at-rules and multi-line rules. That limit is on purpose:
> it nudges anything complex into a real stylesheet.

The paragraph spacing and heading letter-spacing you see come from the inline
channel. View source to see both the `<link>` and the `<style>` in the head.
