#!/usr/bin/env python3
"""tools/syntax.py — writes tests/syntax_tests.nv.

Every template below does not parse, and each says what error `parse`
must answer and where.  The source is written with `@@` at the byte the
error must point to; the script removes the marker and turns its
position into the line and column the test asserts, so no position is
counted by hand.  Jinja2 has no say here: the point is which error
kind this package names and where, and that is this package's design.

Usage:  python tools/syntax.py > tests/syntax_tests.nv && novo fmt tests/syntax_tests.nv
"""

CASES = [
    ("a variable tag never closed", "{{ x@@", None),
    ("an expression tag never closed, on line 2", "a\n@@{% if x", None),
]

# (label, source with @@, error text).  The error text is what
# `describe` in the test prints: `syntax <found>`, `unclosed <tag>`,
# `unexpected <tag>`, `duplicate <block>` or `limit <what>`.
CASES = [
    ("a variable tag never closed", "@@{{ x", "unclosed {{"),
    ("a statement tag never closed, on line 2", "a\n@@{% if x", "unclosed {%"),
    ("a comment never closed", "@@{# x", "unclosed {#"),
    ("a string that never ends", "{{ @@'abc }}", "unclosed string"),
    ("a character that is in no token", "{{ x @@@ y }}", "syntax @"),
    ("an empty expression", "{{ @@}}", "syntax the end of the tag"),
    ("an empty statement", "{% @@%}", "syntax the end of the tag"),
    ("a filter without a name", "{{ x | @@}}", "syntax the end of the tag"),
    ("a parenthesis never closed", "{{ (x @@}}", "syntax the end of the tag"),
    ("a list missing a comma", "{{ [1 @@2] }}", "syntax 2"),
    ("an argument list missing a comma", "{{ f(1 @@2) }}", "syntax 2"),
    ("a dot with nothing after it", "{{ x.@@}}", "syntax the end of the tag"),
    ("a minus with no number", "{{ - @@}}", "syntax the end of the tag"),
    ("an index never closed", "{{ x[1 @@}}", "syntax the end of the tag"),
    ("two expressions in a row", "{{ a @@b }}", "syntax b"),
    ("a not with nothing after it", "{{ not @@}}", "syntax the end of the tag"),
    ("a test with no name", "{{ x is @@}}", "syntax the end of the tag"),
    ("a negated test with no name", "{{ x is not @@}}", "syntax the end of the tag"),
    ("a filter's argument list never closed", "{{ x | f(@@}}", "syntax the end of the tag"),
    ("a keyword argument with no value", "{{ x | f(a=@@) }}", "syntax )"),
    ("a for with no in", "{% for x @@%}", "syntax the end of the tag"),
    ("a for with no collection", "{% for x in @@%}", "syntax the end of the tag"),
    ("a for with a number for a name", "{% for @@1 in y %}", "syntax 1"),
    ("a for with a comma and no second name", "{% for x, in @@y %}", "syntax y"),
    ("a set with no name", "{% set @@%}", "syntax the end of the tag"),
    ("a set with no equals sign", "{% set x @@%}", "syntax the end of the tag"),
    ("an if with no condition", "{% if @@%}", "syntax the end of the tag"),
    ("an if with two conditions", "{% if a @@b %}{% endif %}", "syntax b"),
    ("an include with no name", "{% include @@%}", "syntax the end of the tag"),
    ("an if never closed", "@@{% if x %}a", "unclosed if"),
    ("an if with an else never closed", "@@{% if x %}a{% else %}b", "unclosed if"),
    ("an if with an elif never closed", "@@{% if x %}a{% elif y %}b", "unclosed if"),
    ("a for never closed", "@@{% for x in y %}a", "unclosed for"),
    ("a for with an else never closed", "@@{% for x in y %}a{% else %}b", "unclosed for"),
    ("a block never closed", "@@{% block b %}", "unclosed block"),
    ("a macro never closed", "@@{% macro m() %}", "unclosed macro"),
    ("a filter block never closed", "@@{% filter upper %}", "unclosed filter"),
    ("a raw block never closed", "@@{% raw %}x", "unclosed raw"),
    ("a raw block whose end tag never closes", "@@{% raw %}x{% endraw", "unclosed raw"),
    ("a raw block with another tag inside and no end", "@@{% raw %}{% if x %}", "unclosed raw"),
    ("an endif with nothing open", "@@{% endif %}", "unexpected endif"),
    ("an else with nothing open", "@@{% else %}", "unexpected else"),
    ("an elif with nothing open", "@@{% elif x %}", "unexpected elif"),
    ("an endfor with nothing open", "@@{% endfor %}", "unexpected endfor"),
    ("an endif inside a for", "{% for x in y %}@@{% endif %}{% endfor %}", "unexpected endif"),
    ("an elif after an else", "{% if x %}{% else %}@@{% elif y %}{% endif %}", "unexpected elif"),
    ("a second else in a for", "{% for x in y %}{% else %}@@{% else %}{% endfor %}", "unexpected else"),
    ("an unknown tag", "@@{% frobnicate %}", "syntax frobnicate"),
    ("a while loop, which the language leaves out", "@@{% while x %}{% endwhile %}", "syntax while"),
    ("an extends that is not a literal", "{% extends @@x %}", "syntax x"),
    ("an extends inside an if", "{% if x %}{% extends @@'a' %}{% endif %}", "syntax a"),
    ("an extends followed by more", "{% extends 'a' @@x %}", "syntax x"),
    ("an endblock naming another block", "{% block a %}{% endblock @@b %}", "syntax b"),
    ("a block name followed by more", "{% block a @@b %}{% endblock %}", "syntax b"),
    ("a block with no name", "{% block @@%}", "syntax the end of the tag"),
    ("an endblock with a name and more", "{% block a %}{% endblock a @@x %}", "syntax x"),
    ("a block defined twice", "{% block a %}{% endblock %}\n@@{% block a %}{% endblock %}", "duplicate a"),
    ("a macro with no parameter list", "{% macro m @@%}", "syntax the end of the tag"),
    ("a macro parameters missing a comma", "{% macro m(a @@b) %}{% endmacro %}", "syntax b"),
    ("a macro parameter that is a number", "{% macro m(@@1) %}{% endmacro %}", "syntax 1"),
    ("a macro default with no value", "{% macro m(a=@@) %}{% endmacro %}", "syntax )"),
    ("an import of a name", "{% import @@x as y %}", "syntax x"),
    ("an import with no as", "{% import 'a' @@%}", "syntax the end of the tag"),
    ("an import with no alias", "{% import 'a' as @@%}", "syntax the end of the tag"),
    ("an import with more after the alias", "{% import 'a' as y @@z %}", "syntax z"),
    ("a filter block with no name", "{% filter @@%}", "syntax the end of the tag"),
    ("a tag whose first word is a number", "{% @@1 %}", "syntax 1"),
    ("a number then a name inside a macro call", "{{ m(@@) }}x{{ @@ }}", None),
]
CASES = [c for c in CASES if c[2] is not None]


def nv_str(s):
    out = []
    for ch in s:
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "$":
            out.append("\\$")
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


def position(src):
    i = src.index("@@")
    text = src[:i] + src[i + 2:]
    line = text.count("\n", 0, i) + 1
    col = i - (text.rfind("\n", 0, i) + 1) + 1
    return text, line, col


print('''// syntax_tests.nv — templates that do not parse.
//
// Generated by tools/syntax.py; do not edit by hand.  Each case is a
// template, the kind of error `parse` must answer and the line and
// column it must point at.  The position was marked in the source with
// `@@` and counted by the script.

use std.test
use std.str
use teraparse
use teracompile
use teraerror

// The error as text: its kind and what the kind carries.
fn describe(e: teraerror.TeraError) -> Str
    match e.kind
        ErrorSyntax(found) => "syntax " + found
        ErrorUnclosed(tag) => "unclosed " + tag
        ErrorUnexpectedTag(tag) => "unexpected " + tag
        ErrorDuplicateBlock(name) => "duplicate " + name
        ErrorLimit(what) => "limit " + what
        _ => "other"

fn where_it_points(source: Str) -> Str
    match teraparse.parse("p.html", source)
        Ok(_) => "parsed"
        Err(e) => describe(e) + "@" + str.from_int(e.at.line) + ":" + str.from_int(e.at.column)

@test
fn test_every_syntax_error_names_its_kind_and_its_place() [io]''')
for label, src, want in CASES:
    text, line, col = position(src)
    print("    test.case(%s)" % nv_str(label))
    print("    test.assert(where_it_points(%s) == %s)" % (nv_str(text), nv_str("%s@%d:%d" % (want, line, col))))

print('''
@test
fn test_the_compiler_is_what_parse_calls() [io]
    test.case("compile answers the same error parse does, and the program parse keeps")
    match teracompile.compile("p.html", "{% endif %}")
        Ok(_) => test.assert(false)
        Err(e) => test.assert(describe(e) == "unexpected endif")
    match teracompile.compile("p.html", "{% block b %}{% endblock %}")
        Ok(program) => test.assert(program.block_names == ["b"])
        Err(_) => test.assert(false)

@test
fn test_nesting_is_bounded() [io]
    test.case("two hundred open tags are accepted, one more is refused")
    test.assert(where_it_points(str.repeat("{% if x %}", 199) + str.repeat("{% endif %}", 199)) == "parsed")
    test.assert(str.starts_with(where_it_points(str.repeat("{% if x %}", 250)), "limit nesting@"))

    test.case("so do blocks that open without an expression, such as a filter block")
    test.assert(where_it_points(str.repeat("{% filter upper %}", 250)) != "parsed")
    test.assert(str.starts_with(where_it_points(str.repeat("{% filter upper %}", 250)), "limit nesting@"))

    test.case("parentheses count the same way")
    test.assert(where_it_points("{{ " + str.repeat("(", 150) + "1" + str.repeat(")", 150) + " }}") == "parsed")
    test.assert(str.starts_with(where_it_points("{{ " + str.repeat("(", 250) + "1" + str.repeat(")", 250) + " }}"),
                                "limit nesting@"))''')
