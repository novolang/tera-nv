# tera-nv

A **template** is a document with holes in it: text, plus places where
a value is substituted and places where a section repeats or is
omitted. [Tera](https://keats.github.io/tera/) is a template language
for Rust, closely modelled on Python's
[Jinja2](https://jinja.palletsprojects.com/). This package implements
that language in novo-lang, with the filesystem taken out of it: a
template is parsed once from text the caller supplies and rendered many
times. Its escaping is
[html-nv](https://novo-lang.org/packages/html-nv)'s.

**Status: NOT IMPLEMENTED — interface only.** Every function is
declared with its full signature, but every body is a `todo()` that
panics when called. The package is published so its design can be
reviewed and depended on before it is implemented. Version 0.1.0 will
be the first working release.

## What the language is

`{{ title }}` is an **expression**: the value of `title`, rendered into
the output. A path with dots reaches into a value, so
`{{ user.name }}` reads the `name` entry of `user`.

`{% if %}`, `{% elif %}`, `{% else %}` and `{% endif %}` include a
section conditionally. `{% for x in items %}` repeats one, and inside
it `loop.index`, `loop.first` and `loop.last` describe the position. A
`{% for %}` may carry an `{% else %}` for the case where the collection
is empty. `{% set %}` names a value for the rest of the template.
`{# ... #}` is a comment.

A **filter** transforms a value, written `{{ title | upper }}`. Filters
take arguments. A **test** asks a question, written
`{% if x is defined %}`. Both are **registries**: a named set of
functions the caller can add to or remove from.

**Inheritance** is how one template reuses another's structure. A
parent defines named holes with `{% block name %}`. A child says
`{% extends "base.html" %}` and fills them with its own
`{% block name %}`. `{{ super() }}` inside a child's block renders the
parent's version of it. `{% include "header.html" %}` renders another
template in place.

**Autoescaping** means that a substituted value has its HTML
metacharacters replaced, so a value containing `<script>` appears on
the page as text rather than running. It is on by default here, chosen
by the template's name, and `{{ x | safe }}` turns it off for one
value.

A **template set** is this package's whole loading model. It holds
templates by name, in memory. `extends` and `include` resolve inside
it, and the caller fills it: this package declares no effects and opens
no file.

## Install

```
novo pkg add tera-nv
```

## Example

```novo
use teraerror
use teraparse
use terarender
use teraval

fn main() [io]
    // A set of templates, held by name. This package never opens a file.
    match teraparse.set_add(teraparse.set_new(), "page.html",
                            "<h1>{{ title }}</h1>")
        Err(e) => println(teraerror.one_line(e))
        Ok(set) =>
            // Every name the set's templates reference and it does not
            // hold. The caller reads those and adds them.
            for name in teraparse.set_missing(set)
                println("still needed: ${name}")

            // The values the template sees.
            let ctx = teraval.context_insert(teraval.context_new(),
                                             "title", ValueStr("Hello & welcome"))

            // Render. The name ends in `.html`, so `{{ title }}` is
            // escaped and the ampersand comes out as `&amp;`.
            match terarender.render_str(set, "page.html", ctx)
                Ok(html) => println(html)
                Err(e)   => println(teraerror.report(e, teraparse.set_sources(set)))
```

Build and test with `novo pkg build` and `novo test`. Today `novo test`
fails on purpose: every test reaches a
`not implemented: tera-nv.<module>.<fn>` panic. The tests are the
specification the implementation will have to satisfy.

## What the package contains

| Module | Contents |
| --- | --- |
| `teraerror` | What went wrong, where in which template, and the chain of includes and blocks that reached it. |
| `teraval` | The values a template sees, the context, and the lookup, truthiness and comparison rules. |
| `teraparse` | A template parsed once, the set of them, the escaping rule and the render limits. |
| `terafilter` | The filter and test registries, and the builders for adding to them. |
| `terarender` | Rendering a template into a buffer the caller owns, and the escape the renderer uses. |

## How to choose an entry point

**`teraparse.set_add` and `terarender.render_str` are the ordinary
path.** Build the set once, render many times.

**`terarender.render` appends to a buffer the caller owns** and
`render_with` takes the filter and test registries and the limits.
`render_block` renders one block of one template, which is what an
endpoint answering a fragment wants.

**`terarender.render_one` renders a template with no set at all**, for
a template with no `extends` and no `include`.

**`teraparse.set_check` runs at build time.** It finds a block a child
overrides that no parent defines, an `extends` cycle and a missing
parent, before anything is rendered.

**`teraparse.set_missing` drives loading.** See rule 1.

## The rules a user needs

1. **Loading is a loop between this package and the caller.** Add what
   you have with `set_add`, ask `set_missing` for every name the set's
   templates reference and do not hold, read those, add them, and ask
   again. A set can therefore come from a directory, a zip archive, a
   database, an HTTP response or a compiled-in constant with no change
   here.
2. **`set_missing` cannot be complete, and `terarender.missing` is the
   other half.** `{% include name_var %}` computes its name during the
   render, so it cannot be reported before one. The render's error
   carries the name, and the caller reads it and renders again.
3. **Autoescaping is on, and it is decided by the template's name.**
   `.html`, `.htm`, `.xml` and `.xhtml` are escaped and everything else
   is not, which is Tera's own rule. It gets a site generator's `.html`
   layouts and its `.txt` mail templates both right with no
   configuration. `EscapeAlways` and `EscapeNever` are the named
   overrides.
4. **The escape is html-nv's `escape_attr`, everywhere.** It replaces
   five characters: `&`, `<`, `>`, `"` and `'`. A template engine
   cannot tell whether a `{{ }}` sits inside an attribute, and escaping
   more than necessary is a rendering nobody notices while escaping
   less is a hole. `terarender.escape` republishes it, so a caller
   writing a filter that produces markup escapes the way the renderer
   does.
5. **`| safe` is the whole escape hatch.** It is at the point where it
   is needed and it can be searched for. A caller rendering templates
   it does not trust removes it:
   `terafilter.without_filter(builtin_filters(), "safe")`.
6. **A null value renders as empty and is false.** That is Jinja2's
   rule and what a template author expects.
   `teraval.is_truthy` is the whole predicate.
7. **A map iterates in insertion order.** `ValueMap` holds pairs rather
   than a hash, because a page whose navigation reorders itself between
   two renders of the same data has a diff nobody can read.
8. **Three limits bound a render.** They are checked during it, not
   after.

   | `TeraLimits` field | What it bounds | `default_limits()` |
   | --- | --- | --- |
   | `max_depth` | How deeply includes and extends nest | 32 |
   | `max_iterations` | Loop iterations in one render | 10,000,000 |
   | `max_output` | Bytes one render may produce | 64 MiB |

9. **A missing include is an error, not an empty expansion.** A
   production build that silently dropped a header is worse than one
   that failed. A development server that wants the other behaviour
   catches `ErrorTemplateNotFound` and carries on.
10. **An error carries a chain, not a line.** A page extends a base,
    which includes a header, which includes a navigation bar, and the
    variable that was missing was missing in the navigation bar,
    referenced from a block the page defined. `TeraError` carries the
    kind, a span and a list of frames. `teraerror.report` renders the
    whole chain with the source lines, `one_line` is the log form, and
    `missing_template` is the one question a caller asks without
    matching on the error.
11. **A context holds values, never functions.** `TeraValue` has no
    function variant. Logic goes in a filter, and a filter is something
    the caller enumerated, so a template can reach nothing the caller
    did not put in the context or the registry.
12. **A template is parsed, so content is content.** A page whose body
    contains the literal text `{{ title }}`, such as a page documenting
    this syntax, renders that text. An engine that substituted into a
    string and substituted again would replace it.

## What the language includes

`{{ }}` with dotted paths and indices. Filters with arguments.
`{% if %}`, `{% elif %}`, `{% else %}`. `{% for %}` with `{% else %}`
and the `loop` variables. `{% set %}`. `{% include %}`.
`{% extends %}`, `{% block %}` and `{{ super() }}`. `{% macro %}` and
`{% import %}`. `{% filter %}` blocks. `{% raw %}`. `{# #}` comments.
`is` tests. The comparison and boolean operators. Whitespace control
with `{%-` and `-%}`.

## What is not included

- **`{% while %}`.** A template that can loop unboundedly can hang a
  render. Every loop here is over a finite collection, and
  `max_iterations` bounds even that.
- **Arbitrary expressions.** No arithmetic beyond what a comparison
  needs, no method calls, and no way to reach anything the caller did
  not register. A template that can call arbitrary code is a program
  with an awkward syntax.
- **Loading templates from anywhere.** No paths, no globs, no
  directories. See rule 1.
- **A `markdown` filter or a `date` filter.** The registry is a value,
  so a caller that wants one registers it in a line:
  `terafilter.with_filter(terafilter.builtin_filters(), terafilter.filter("markdown", to_html))`.
  A package in the web category depending on a text package to supply a
  filter most callers will not use is the wrong direction.
- **Compiling templates to code.** That needs a build step and a macro
  system, and it costs a template being a file somebody can edit.
- **Internationalisation.** A `t` filter over a catalogue the caller
  supplies is how this package and
  [i18n-nv](https://novo-lang.org/packages/i18n-nv) meet.
- **A sandbox beyond what the language already is.** There is no way to
  reach anything the caller did not register, and `TeraLimits` bounds
  the resources. There is no third kind of sandbox.
- **Anything that reads, fetches or consults a clock.** This package
  declares no effects.
- **A build for a microcontroller.** The value model is a growable tree
  of strings.

## Related packages

- [html-nv](https://novo-lang.org/packages/html-nv) supplies the
  escape, and nothing else: this package does not parse its own output.
  One escape used by both packages is one rule on the page rather than
  two. This package depends on it.
- [markdown-nv](https://novo-lang.org/packages/markdown-nv) turns
  Markdown into HTML, and is what a `markdown` filter would call.
- [static-nv](https://novo-lang.org/packages/static-nv) serves the
  files a rendered site becomes.
- [rss-nv](https://novo-lang.org/packages/rss-nv) writes a feed for the
  same site, and is a writer rather than a template.
- [i18n-nv](https://novo-lang.org/packages/i18n-nv) holds the message
  catalogue a `t` filter would read.

## Tests

```bash
novo test tests/teraval_tests.nv      # the value model's rules
novo test tests/teraparse_tests.nv    # the set, inheritance, and the errors
novo test tests/terarender_tests.nv   # the language, and autoescaping first
```

The reference implementations are Tera, for the template set, the
inheritance model, the registries and the escape-by-suffix rule, and
Jinja2, for the language itself: the `loop` variables, the truthiness
rule, `{{ super() }}`, and the decision that a template is not a
programming language. MiniJinja is the reference for the value model
being the one the caller's data is already in, and Askama is the
reference for what compiling templates costs.

The oracles are Tera's and Jinja2's own suites, which are pairs of a
template and its output. The autoescaping corpus is this package's own,
because that part is a security property rather than a feature.

The suite asserts that a value containing `<script>` renders escaped in
a `.html` template and unescaped in a `.txt` one, that `| safe` turns
escaping off for one value and nothing else, that a null value renders
empty and is false, that a map iterates in insertion order, that a
block a child overrides and no parent defines is reported by
`set_check` rather than rendering an empty page, that an extends cycle
is refused, and that each of the three limits stops a render.

The tests compile today and fail at run, each on the
`not implemented: tera-nv.<module>.<fn>` panic that is its body. That
is the expected state of an interface release. They turn green one at a
time as bodies land.

## Implementation status

| Item | Implemented |
| --- | --- |
| Every `pub struct` and `pub enum` in the five modules | the types are declared |
| `teraerror.report`, `.one_line`, `.missing_template`, `TeraError.message` | no |
| `teraval.context_new`, `.context_insert`, `.context_get`, `.context_names`, `.context_from_map` | no |
| `teraval.lookup`, `.is_truthy`, `.to_display`, `.to_json`, `.type_name`, `.equals`, `.compare` | no |
| `teraparse.default_limits`, `.parse` | no |
| `teraparse.template_name`, `.template_source`, `.references`, `.extends_name` | no |
| `teraparse.blocks`, `.variables`, `.filters_used` | no |
| `teraparse.set_new`, `.set_with`, `.set_add`, `.set_add_parsed`, `.set_names`, `.set_get` | no |
| `teraparse.set_missing`, `.set_check`, `.set_sources`, `.escapes_name` | no |
| `terafilter.builtin_filters`, `.no_filters`, `.with_filter`, `.without_filter` | no |
| `terafilter.filter_names`, `.get`, `.filter`, `.refuse` | no |
| `terafilter.builtin_tests`, `.with_test`, `.test_names` | no |
| `terarender.render`, `.render_with`, `.render_str`, `.render_one`, `.render_block` | no |
| `terarender.escape`, `.escape_into`, `.loop_variable_names`, `.missing` | no |

## Licence

Apache-2.0. See `LICENSE`.

<!-- docs/writing-a-readme.md is the style guide for this page. -->
