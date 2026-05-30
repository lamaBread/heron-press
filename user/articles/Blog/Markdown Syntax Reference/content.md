This article is a compact torture-test of the Markdown parser (a Python port
of Parsedown 1.7.4). If something renders correctly here, it will render in
your own articles.

===Headings===

# Heading 1
## Heading 2
### Heading 3
#### Heading 4

Setext headings also work:

Alternate H1
============

Alternate H2
------------

===Inline elements===

- **Bold** and __bold__
- *Italic* and _italic_
- ***Bold italic***
- ~~Strikethrough~~
- `inline code`
- A [reference link][ref] defined elsewhere
- An ![inline image](./does-not-exist.png) (intentionally broken to show alt text)

[ref]: https://example.com "Reference links resolve by label"

===Nested lists===

1. Top level
    1. Nested ordered
    2. Second nested
        - mixed bullet
        - another
2. Back to top
    - bullet under ordered

===Nested block quotes===

> Level one.
>
> > Level two.
> >
> > > Level three, with `code` and **bold**.

===Tables with alignment===

| Left | Center | Right |
|:-----|:------:|------:|
| a    |   b    |     c |
| long | mid    |     1 |

===Horizontal rule===

Above the rule.

---

Below the rule.

===Fenced code (multiple languages)===

```bash
python Heron.py --clean
```

```html
<p>HTML inside a code fence is escaped, not rendered.</p>
```

That covers the constructs you will reach for day to day.
