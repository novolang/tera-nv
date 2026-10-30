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

Build and test with `novo pkg build` and `novo test`.

## What the package contains

| Module | Contents |
| --- | --- |
| `teraerror` | What went wrong, where in which template, and the chain of includes and blocks that reached it. |
| `teraval` | The values a template sees, the context, and the lookup, truthiness and comparison rules. |
| `teraparse` | A template parsed once, the set of them, the escaping rule and the render limits. |
| `terafilter` | The filter and test registries, and the builders for adding to them. |
| `terarender` | Rendering a template into a buffer the caller owns, and the escape the renderer uses. |
| `teracompile`, `teranode` | The parser and the tree it makes. Used by `teraparse`; a program does not call them. |

## How to choose an entry point

**`teraparse.set_add` and `terarender.render_str` are the ordinary
path.** Build the set once, render many times.

**`terarender.render` appends to a buffer the caller owns** and
`render_with` takes the filter and test registries and the limits.
`render_block` renders one block of one template, which is what an
endpoint answering a fragment wants.

**`terarender.render_one` renders a template with no set at all**, for
a template with no `extends` and no `include`. It is autoescaped, as
if its name ended in `.html`.

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
   overrides. The name that decides is the one the render was asked
   for, and the templates it extends and includes follow it.
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
6. **Output that is markup already is not escaped again.** That is the
   result of a macro, of `super()`, and of a filter chain that has
   `safe`, `escape` or `escape_xml` in it.
7. **A null value renders as empty and is false.** That is Jinja2's
   rule and what a template author expects.
   `teraval.is_truthy` is the whole predicate.
8. **A map iterates in insertion order.** `ValueMap` holds pairs rather
   than a hash, because a page whose navigation reorders itself between
   two renders of the same data has a diff nobody can read.
9. **Three limits bound a render.** They are checked during it, not
   after.

   | `TeraLimits` field | What it bounds | `default_limits()` |
   | --- | --- | --- |
   | `max_depth` | How deeply includes and extends nest | 32 |
   | `max_iterations` | Loop iterations in one render | 10,000,000 |
   | `max_output` | Bytes one render may produce | 64 MiB |

10. **A missing include is an error, not an empty expansion.** A
   production build that silently dropped a header is worse than one
   that failed. A development server that wants the other behaviour
   catches `ErrorTemplateNotFound` and carries on.
11. **An error carries a chain, not a line.** A page extends a base,
    which includes a header, which includes a navigation bar, and the
    variable that was missing was missing in the navigation bar,
    referenced from a block the page defined. `TeraError` carries the
    kind, a span and a list of frames. `teraerror.report` renders the
    whole chain with the source lines, `one_line` is the log form, and
    `missing_template` is the one question a caller asks without
    matching on the error.
12. **A context holds values, never functions.** `TeraValue` has no
    function variant. Logic goes in a filter, and a filter is something
    the caller enumerated, so a template can reach nothing the caller
    did not put in the context or the registry.
13. **A template is parsed, so content is content.** A page whose body
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

## Differences from Tera and Jinja2

Tera and Jinja2 share most of their syntax. Where this package does
something other than Jinja2 does, it is listed here. The right-hand
column was checked against Jinja2 3.1.

| Construct | This package | Jinja2 |
| --- | --- | --- |
| A name or field that is not there | An error naming it | An empty string, unless run strict |
| `{{ true }}` and `{{ false }}` | `true`, `false` | `True`, `False` |
| `{{ [1, 2] }}` and a map | JSON text | Python text |
| `a and b`, `a or b` | A bool | One of the operands |
| A macro's access to the template's variables | None | All of them |
| Calling a macro | `m(x)`, `ns::m(x)` or `ns.m(x)` | `m(x)` or `ns.m(x)` |
| A filter's arguments | By position; a name before `=` is read and ignored | By position or name |
| `for k, v in map` | The pairs, in insertion order | Needs `map.items()` |
| `for i, x in list` | The index from 0 and the item | The items must be pairs |
| The test for null | `is null` | `is none` |
| Arithmetic, `~`, `{% while %}`, `{% break %}` | Not in the language | Arithmetic and `~` are |

A filter that Jinja2 also has can still answer differently. The ones
that do:

| Filter | This package |
| --- | --- |
| `upper`, `lower`, `capitalize`, `title` | Change ASCII letters only. |
| `truncate(n)` | Keeps the first `n` characters and adds nothing, unless a second argument gives the text to add when it cut. |
| `sort`, `unique` | Compare strings by bytes. Jinja2 ignores case by default. |
| `round` | Halves go away from zero. Python rounds halves to even. |
| `striptags` | Removes what lies between `<` and `>`. It does not collapse white space or read entities. |
| `escape_xml` | Writes the apostrophe as `&apos;`. |
| `slice(start, end)` | Takes the items from `start` up to `end`. Jinja2's `slice` splits a list into columns. |
| `default(v)` | Replaces null and a name that is not there. A true second argument also replaces any false value. |
| `filesizeformat` | Powers of 1,000 with one decimal, as in Jinja2: `999 Bytes`, `1.0 kB`. |
| `slugify`, `nth`, `group_by`, `linebreaks`, `filter` | Defined here. Jinja2 has no filter of these names. |

## Tests

```bash
novo test tests/oracle_tests.nv   # cases whose expected text Jinja2 produced
novo test tests/lang_tests.nv     # Tera's rules, derived by hand
novo test tests/filter_tests.nv   # every filter and test, called directly
novo test tests/syntax_tests.nv   # templates that do not parse, and where
novo test tests/error_tests.nv    # messages, reports and positions
novo test tests/teraval_tests.nv
novo test tests/teraparse_tests.nv
novo test tests/terarender_tests.nv
bash tests/coverage.sh            # line coverage of src/, merged across the suites
```

Jinja2 3.1 is the reference for the part of the language it shares with
Tera. `tools/oracle.py` renders each case in Jinja2, set to behave as
Tera does where a setting decides it: an unknown name is an error, the
last newline is kept, and the name's suffix decides autoescaping. The
script writes `tests/oracle_tests.nv` from the answers. Jinja2 writes a
double quote as `&#34;` and html-nv writes `&quot;`, so the script
rewrites the first to the second, and nothing else. The script also
compares `to_json` with Python's `json.dumps` in its compact form.

Where Tera and Jinja2 differ, or only Tera has the construct, the
expected text in `tests/lang_tests.nv` and `tests/filter_tests.nv`
was derived by hand, and each case states the rule it follows.
`tools/syntax.py` writes `tests/syntax_tests.nv` from templates that
mark where each error must point.

The suites measure 100% of the lines under `src/`.

## Licence

Apache-2.0. See `LICENSE`.

<!-- docs/writing-a-readme.md is the style guide for this page. -->
