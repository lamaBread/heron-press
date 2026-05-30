Welcome! This article is the front door of the demo. It shows the everyday
Markdown you will use most, plus Heron's own **section markers** and
**image-box** syntax.

![[A placeholder hero banner]](./imgs/hero.png) {The image-box syntax renders a figure with a caption.}

Notice the line above: `![[alt]](path) {caption}` becomes a captioned figure.
Drop the `{...}` and you get a plain image.

===Text formatting===

You get the usual inline marks: **bold**, *italic*, ~~strikethrough~~, and
`inline code`. Links can be [internal](/about/) or
[external](https://example.com). Bare URLs autolink too:
<https://example.com>.

> Block quotes work, and they can nest:
>
> > like this, one level deeper.

===Lists and tables===

Ordered and unordered lists, including nesting:

1. First step
2. Second step
   - a nested bullet
   - another, with `code`
3. Third step

A table with column alignment:

| Feature        | Build-time | Runtime |
|:---------------|:----------:|--------:|
| Markdown       |     ✓      |         |
| Search (BM25)  |            |    ✓    |
| Image → WebP   |     ✓      |         |

===Code blocks===

Fenced code blocks keep their language hint and never execute — even `<?php`:

```python
def greet(name: str) -> str:
    return f"Hello, {name}!"
```

======

The six-equals line above explicitly closed the section. Everything reads
top-to-bottom as plain, server-rendered HTML — no client-side JavaScript is
required to view this page.

For an exhaustive syntax list see
[Markdown Syntax Reference](/markdown-syntax/), and to learn how images become
multi-resolution WebP see [Working with Images](/working-with-images/).
