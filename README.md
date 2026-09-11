# tera-nv

**Status: NOT IMPLEMENTED — interface only.**

Every public function below is published with its signature and its
effect row, and every body is `todo()`. Installing this package works;
calling it panics with `not implemented`.

## What this is

The Tera and Jinja2 template language, with the filesystem taken out of
it.

- `teraval` — the values a template sees, and the context;
- `teraparse` — a template parsed once, and a **set** of them;
- `terarender` — a template and a context into bytes the caller owns;
- `terafilter` — filters and tests, as registries the caller extends;
- `teraerror` — what went wrong, where, and through which include.

```
novo pkg add tera-nv
novo pkg build
novo test
```

## The one example that will work — the host loop

```novo ignore
use teraparse
use terarender

// `core` cannot open a file.  So the core says what it needs and the
// host reads it — which is the whole of how `{% extends %}` works
// here, and the reason this package has a layer at all.
fn load_all(names: [Str], read: fn(Str) -> Str) -> teraparse.TeraSet [fs]
    var set = teraparse.set_new()
    for name in names
        set = add(set, name, read(name))

    var missing = teraparse.set_missing(set)
    while list.len(missing) > 0
        for name in missing
            set = add(set, name, read(name))     // the host performs
        missing = teraparse.set_missing(set)
    set
```

## The load-bearing interface

```novo ignore
pub fn set_missing(s: TeraSet) -> [Str] []
pub fn missing(e: TeraError) -> ?Str []
```

**A template that inherits needs another template, and a `core`
package cannot open a file.** `TeraSet` holds templates by name, in
memory; `set_missing` reports every name the set's templates reference
and it does not hold; the host reads those and adds them; repeat.
That is the shape the layer design asks of a `core` package — it takes
values in and returns requested actions out, and the host is the only
party that performs anything.

It is also why a template set can come out of a zip archive, a
database, an HTTP response or a compiled-in constant with no change to
this package.

**`terarender.missing` is the other half, and it exists because
`set_missing` cannot be complete.** `{% include name_var %}` computes
its name at render time, so it cannot be reported before the render.
Rather than promising completeness this package does not have, the
render's error carries the name the host has to read, and the host
handles it with the same loop. Saying so is better than a promise that
quietly does not hold.

## Autoescaping, which is a security property rather than a feature

**On by default, and it is html-nv's escape.** A template engine for
the web whose default is not to escape produces cross-site scripting;
one whose escape disagrees with the HTML package the same program uses
produces a page with two escaping rules in it.

`{{ x }}` in an autoescaped template is `htmlsafe.escape_attr` — five
characters, `& < > " '` — **everywhere**, including outside attributes
where three would do. A template engine cannot tell whether a `{{ }}`
is inside an attribute, and escaping more than necessary is a rendering
nobody notices while escaping less is a hole.

`{{ x | safe }}` turns it off for one value. That is the whole escape
hatch, it is at the point it is needed, and it is greppable. A caller
rendering templates it does not trust removes it in one line:
`terafilter.without_filter(builtin_filters(), "safe")`.

**Which templates are escaped is decided by name** — `.html`, `.htm`,
`.xml`, `.xhtml` are, everything else is not. That is Tera's own rule
and it gets a site generator's `.html` layouts and its `.txt` mail
templates both right with no configuration. `EscapeAlways` and
`EscapeNever` are the named overrides.

## What the site generator's engine does, and what it does not

The plan's row says *the site generator's template engine graduates*.
It is worth being exact about what that is, because it is smaller than
the word "engine" suggests.

`orbit/static-site-generator/src/main.nv` has two functions —
`render_template` and `expand_includes`, about forty lines between
them:

```novo ignore
fn render_template(tpl: Str, content: Str, title: Str, sidebar: Str,
                   theme_dir: Str) -> Str [io, fs]
    var out = tpl
    out = replace_all(out, "{{ content }}", content)
    out = replace_all(out, "{{ title }}",   title)
    out = replace_all(out, "{{ sidebar }}", sidebar)
    out = expand_includes(out, theme_dir)
    out
```

Three named substitutions and `{{ include "path" }}`, expanded in a
loop with a budget of 16.

**What it does that this package must not lose:**

- **The include budget.** Sixteen expansions, then it stops. A template
  that includes itself terminates. `TeraLimits.max_depth` is the same
  idea, given a name and a reported error instead of a silent stop.
- **A missing include is a warning and an empty expansion**, not a
  failure — the build carries on and says so. That is the right
  behaviour for a dev server, and it is reachable here by catching
  `ErrorTemplateNotFound` and continuing; it is not the default,
  because a production build that silently dropped a header is worse
  than one that failed.

**What it does not do, and this package does:**

| the generator | here |
| --- | --- |
| three hard-coded variable names | any name, and dotted paths into a value |
| no conditionals | `{% if %}` / `{% elif %}` / `{% else %}` |
| no loops — the sidebar is built by Novo code that concatenates strings | `{% for %}`, with `loop.index`, `loop.first`, `loop.last` and an `{% else %}` for the empty case |
| no inheritance — every layout is a whole file | `{% extends %}`, `{% block %}`, `{{ super() }}` |
| no filters | a registry of about thirty, which the caller extends |
| no escaping at all | autoescape on, by template name |
| `[io, fs]` — it reads the include from disk as it expands | `[]`; the host reads and `set_missing` says what |
| a missing include prints a warning to stdout | an error value with a template, a line and a chain |
| substitution by `replace_all`, so `{{ content }}` inside the content expands again | parsed once; content is content |

That last row is a real bug rather than a missing feature: the
generator substitutes into a string and then substitutes again, so a
page whose body contains the literal text `{{ title }}` — a page
documenting this template syntax, for instance — has it replaced. A
parsed template cannot do that.

**What happens to the generator's engine.** It is deleted when this
package has bodies, and the migration is small because the generator's
own Novo code is doing the work a template language would: `build_sidebar`
is a `{% for %}`, `build_page_toc` is a nested one, and `render_page`'s
argument list is a context. The sequence is the same one markdown-nv
describes: the site generator moves first, then `orbit/website`'s
pages, and the two packages land together because the generator wants
both.

## The dependency, and the one it does not have

**html-nv, for autoescaping and for nothing else.** The argument is
above: one escape, used by both packages, or two rules in one page.
`terarender.escape` republishes it so that a caller writing a filter
which produces markup escapes exactly the way the renderer would.

What this package does **not** take from html-nv: the parser, the tree,
the selectors, the sanitiser. A template engine does not parse its own
output.

**markdown-nv is not a dependency**, and there is no `markdown` filter.
A `web` package depending on a `text` package to provide a filter most
callers will not use is the wrong direction, and the registry is a
value — a caller that wants it writes three lines:

```novo ignore
let filters = terafilter.with_filter(terafilter.builtin_filters(),
                                     terafilter.filter("markdown", to_html))
```

The same argument covers `date` (calendar-nv's arithmetic) and
anything that would read, fetch or consult a clock (`core`).

## The language, and what is deliberately not in it

**In:** `{{ }}` with dotted paths and indices; filters with arguments;
`{% if %}` / `{% elif %}` / `{% else %}`; `{% for %}` with `{% else %}`
and the `loop` variables; `{% set %}`; `{% include %}`;
`{% extends %}`, `{% block %}` and `{{ super() }}`; `{% macro %}` and
`{% import %}`; `{% filter %}` blocks; `{% raw %}`; `{# #}` comments;
`is` tests; the comparison and boolean operators.

**Out, and why:**

- **`{% while %}`.** A template that can loop unboundedly is a template
  that can hang a render. Every loop here is over a finite collection,
  and `max_iterations` bounds even that.
- **Arbitrary expressions.** No arithmetic beyond what a comparison
  needs, no method calls, no way to reach anything the caller did not
  put in the context or the registry. A template that can call
  arbitrary code is a program with the worst possible syntax.
- **Functions in a context.** `TeraValue` has no function variant, on
  purpose. Logic goes in a filter, and a filter is a thing the caller
  enumerated.
- **Template loading of any kind.** No paths, no globs, no directories.
  That is the layer, and `set_missing` is the answer.
- **Whitespace control** (`{%-` and `-%}`) is **in**, because a
  template that cannot control its own whitespace produces HTML nobody
  can read — but it is the only piece of syntax here that exists purely
  for the look of the output.

## Errors that name the line, and the chain that reached it

A page extends a base, which includes a header, which includes a nav —
and the variable that was missing was missing in the nav, referenced
from a block the page defined. One line number describes none of that.

```text
unknown variable `user.nmae` in `nav.html`, line 4
  4 |   <a href="/u/{{ user.nmae }}">
    |                  ^^^^^^^^^
  included from `header.html`, line 12
  included from `base.html`, line 3
  in block `content` of `page.html`, line 8
```

`TeraError` carries the kind, a `TeraSpan` and a `[TeraFrame]` chain;
`teraerror.report` renders the above, `one_line` is the log form, and
`missing_template` is the one question a host asks without matching on
the error at all.

**`teraparse.set_check` moves the worst of them to build time.** A
block a child overrides that no parent defines — `{% block contnet %}`
— otherwise renders a page with the content silently missing, which is
the single most frustrating template bug there is. `set_check` finds
it, along with extends cycles and missing parents, before anything is
rendered.

## The layer, and the device claim

`core` — no effects. Parsing is arithmetic, rendering appends to the
caller's buffer, and the one thing that would need the machine —
reading another template — is what `set_missing` hands back to the
host.

**No `@tier(embedded)` claim, and none is intended.** The value model
is a growable tree of `Str`, and a device rendering HTML templates is
not a thing. The audit's `core-embedded` row passes as *makes no device
claim*.

## Where the names come from, and the ones that were taken

Public type names are unique across the whole assembly, dependencies
included. This package had the most obvious names to give up, because
every noun a template engine wants is a noun.

| here | the obvious name | why not |
| --- | --- | --- |
| `TeraTemplate` | `Template` | the single most certain collision on the registry — template-nv is a planned row, and `strfmt` is a module already in use |
| `TeraContext` | `Context` | generic enough that four packages will want it |
| `TeraValue`, `TeraPair` | `Value`, `Pair` | `TomlValue`, `YamlValue` and `ConfigValue` are the precedent; `Pair` is already published |
| `TeraSet` | `Set` | `Set` is a **standard-library type** |
| `TeraError`, `TeraSpan`, `TeraFrame` | `Error`, `Span`, `Frame` | `Error` is a standard-library **trait**; `Frame` and `FrameRef` are published by frame-nv; `Span` is a module name in use |
| `TeraFilter`, `TeraFilters` | `Filter`, `Filters` | `ResizeFilter` and `PngFilter` are published, and `Filter` is what a query package will want |
| `TeraTest`, `TeraTests` | `Test` | `std.test` is a standard-library module, and `PropCheck` and `StTestResult` are the precedent for prefixing |
| `TeraEscape`, `TeraLimits`, `TeraRender` | `Escape`, `Limits`, `Render` | `AnsiLimits`, `WsLimits`, `MqttLimits` and `KeyLimits` are all published — `Limits` was gone four times over |
| module `teraparse`, `teraval`, … | `tera`, `template`, `render`, `value`, `error`, `filter` | every one of the six is a name another package will want; `error` in particular is certain |

## The reference implementation

**Tera** for the whole shape: the template set, the inheritance model,
the filter and test registries, and the autoescape-by-suffix rule.
**Jinja2** for the language itself — the `loop` variables, the
truthiness rule, `{{ super() }}`, and the decision that a template is
not a programming language. **MiniJinja** for the observation that the
value model should be the one the caller's data is already in.
**Askama** for what is lost by compiling templates instead, which is
why these are parsed at run time. **The static site generator's
`render_template`** for the include budget, and for the reminder that
a substitution-based engine re-substitutes its own output.

The oracles are Tera's and Jinja2's own suites — the template-and-
output pairs both projects ship — plus this package's own autoescape
corpus, which is the part that is a security property rather than a
feature and so is not taken from anybody else's tests.

Deliberately left out, and where it goes instead:

- **Loading templates from anywhere.** The layer. `set_missing`.
- **A `markdown` or a `date` filter.** markdown-nv and calendar-nv, and
  three lines of registration.
- **Compiling templates to code.** Askama's model, and it needs a
  build step and a macro system; the cost is that a template stops
  being a file somebody can edit.
- **Internationalisation.** i18n-nv's row. A `t` filter over a
  catalogue the caller supplies is how the two meet.
- **Sandboxing beyond what the language already is.** There is no way
  to reach anything the caller did not register, which is the
  sandbox; a resource sandbox is `TeraLimits`, and there is no third
  kind.

## Status

Every function is `todo()`. Three suites, all red, all for the same
reason — every assertion reaches `not implemented: tera-nv.<fn>`, which
is the expected result until the bodies land.

```
novo test --isolate tests/teraval_tests.nv       # the value model's surprises
novo test --isolate tests/teraparse_tests.nv     # the set, the inheritance, the errors
novo test --isolate tests/terarender_tests.nv    # the language, and autoescaping first
```

`novo doc` renders and its examples compile.
