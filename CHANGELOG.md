# Changelog

All notable changes to tera-nv are recorded here. The format is
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
package follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
with the pre-1.0 rule that a breaking change bumps the MINOR number.

## 0.1.0 — 2026-10-29

First implementation of the interface published as 0.0.x.

### Added

- The parser, the renderer, the builtin filters and tests, the set and
  the error reports. Every function of the five modules has a body.
- `teraerror.span_at` and `teraerror.nearest`, which the parser and the
  renderer share and a host may call: the line and column of an
  offset, and the registered name within two edits of a misspelled one.
- `teraval.step`, one path segment applied to a value, which `lookup`
  and the renderer are built on.
- `teracompile` and `teranode`, the parser and the tree it makes. They
  are package-internal; no program is meant to call them.
- `tools/oracle.py` and `tools/syntax.py`, which write
  `tests/oracle_tests.nv` and `tests/syntax_tests.nv`, and
  `tests/coverage.sh`, which measures 100% of the lines under `src/`.

### Changed

- `TeraTemplate.program` is now `teranode.TeraProgram` and not
  `[Int]`. The type was documented as private. This is a breaking
  change to anything that constructed one.
- The parameter of `with_filter`, `without_filter`, `filter_names` and
  `get` that was named `fs` is named `reg`. Calls are unaffected.
- `ErrorUnknownFilter` also reports an unknown test, and
  `ErrorUnexpectedTag("block <name>")` is what `set_check` answers for a
  block a child overrides and no parent defines. `ErrorNoSuchField`
  also reports a missing macro, a `super()` with no parent block and a
  block `render_block` could not find.

### Decisions the interface left open

- A filter chain that contains `safe`, `escape` or `escape_xml`, and the
  result of a macro or of `super()`, is not escaped again.
- `render_one` autoescapes, and names its template `template`.
- `upper`, `lower`, `capitalize` and `title` change ASCII letters only.
- `truncate(n)` keeps `n` characters and adds the optional second
  argument only when it cut. `indent(n)` is `n` spaces and leaves the
  first line and blank lines alone.
- A filter's arguments are taken by position. A name before `=` is
  accepted and ignored, so a template written for Tera's named
  arguments parses.
- `for k, v in list` binds the index and the item. One name over a map
  binds the key.
- Tera's behaviour in the places the two languages differ was taken
  from the interface's documentation; the Tera documentation was not
  available. `tests/lang_tests.nv` and `tests/filter_tests.nv` state
  the rule each expected value follows.

### Known

- A call through a function-valued struct field whose match arm returns
  from inside a `for` loop leaks one object. The registry lookup in
  `terarender` is written as a lookup followed by a call for that
  reason, which is also the plainer shape. The filing is
  `memory-perceus/a-return-in-a-match-arm-on-a-call-through-a-struct-field-leaks-in-a-loop`.

## 0.0.3 — 2026-09-28

The dependency ranges move to the dependencies' current releases.  A
pre-1.0 caret range admits only the release it names, so the old
ranges held this package on interface releases, and a program could
not take this package beside those packages' current releases.  No
signature in this package changed.

- html-nv: `^0.0.1` to `^0.1.0`.

## 0.0.2 — 2026-09-15

README rewritten to the package README style guide (docs/writing-a-readme.md); no change to the interface.

## 0.0.1 — 2026-09-11

The **interface**: every signature and every effect row, and no bodies.
`stability = "draft"`, and the release is recorded `implemented = false`.

### Added

- `teraparse` — a template parsed once and rendered many times, and
  `TeraSet` with `set_missing`: the sans-IO answer to
  `{% extends %}`, where the core says which templates it needs and
  the host reads them. `set_check` moves an overridden block that no
  parent defines from a silent hole in a page to a build-time error.
- `teraval` — the JSON value model with int and float kept apart, and
  a context that is a value so a base can be shared across pages.
- `terarender` — the render, appending to the caller's buffer, and
  reporting which templates it used so an incremental build has its
  dependency edge.
- `terafilter` — filters and tests as two registries the caller
  extends, and two namespaces because a test answers a Bool about a
  subject rather than transforming it.
- `teraerror` — a kind, a `TeraSpan`, and the include chain that
  reached it, with `report` rendering the source line and a caret.

### Known

- **Autoescaping is on by default and is html-nv's `escape_attr`** —
  five characters everywhere, because a template engine cannot tell
  whether a `{{ }}` is inside an attribute. `{{ x | safe }}` is the
  whole escape hatch.
- **`set_missing` cannot be complete**, and the README says so: a
  computed include name is only known at render time, so
  `terarender.missing` carries it out of the error instead.
- **html-nv is a path dependency in this tree** and becomes
  `html-nv = "^0.0.1"` at publish. A path dependency is refused by
  `novo pkg publish`.
- **No `{% while %}`, and no arbitrary expressions.** A template that
  can loop unboundedly can hang a render, and one that can call
  arbitrary code is a program with the worst possible syntax.
- **No `markdown` or `date` filter**, deliberately. The registry is a
  value; a caller that wants one registers it in three lines.
- **No `@tier(embedded)` claim.** The value model is a growable tree
  of `Str`.
- **The AST is not public.** `TeraTemplate` is opaque, so adding a tag
  to the language is not a breaking change to a type nobody outside
  this package has a use for.

### Design notes

Public type names are unique across a whole assembly, dependencies
included, and a template engine wants every noun. `TeraTemplate`
because template-nv is a planned package and `strfmt` is a module
already in use; `TeraContext`, `TeraValue` and `TeraPair` on the
precedent of `TomlValue` and `YamlValue`; `TeraSet` because `Set` is a
standard library type; `TeraError`, `TeraSpan` and `TeraFrame` because
`Error` is a standard library trait and frame-nv publishes `Frame`;
`TeraFilter` because `ResizeFilter` and `PngFilter` are published;
`TeraTest` because `std.test` is a standard library module;
`TeraLimits` because `AnsiLimits`, `WsLimits`, `MqttLimits` and
`KeyLimits` are all published. The modules are prefixed because `tera`,
`template`, `render`, `value`, `error` and `filter` are each names
another package will want.

The named first consumer is
`orbit/static-site-generator/src/main.nv`, whose `render_template` and
`expand_includes` are about forty lines: three hard-coded variable
names substituted with `replace_all`, and `{{ include "path" }}`
expanded in a loop with a budget of sixteen. Two of its behaviours are
worth keeping. The budget terminates a template that includes itself,
which `TeraLimits.max_depth` does with a named error instead of a
silent stop. A missing include is a warning and an empty expansion,
which is right for a development server and reachable here by catching
`ErrorTemplateNotFound`.

Its substitution has a defect a parsed template does not: it
substitutes into a string and then substitutes again, so a page whose
body contains the literal text `{{ title }}` has it replaced. The
generator's own Novo code is already doing a template language's work —
`build_sidebar` is a `{% for %}`, `build_page_toc` a nested one, and
`render_page`'s argument list a context.
