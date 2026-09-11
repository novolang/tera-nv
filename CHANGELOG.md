# Changelog

All notable changes to tera-nv are recorded here. The format is
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
package follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
with the pre-1.0 rule that a breaking change bumps the MINOR number.

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
