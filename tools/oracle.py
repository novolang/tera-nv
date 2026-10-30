#!/usr/bin/env python3
"""tools/oracle.py — writes tests/oracle_tests.nv.

Jinja2 is the oracle for the part of the language Jinja2 and Tera
share: variables and paths, the filters the two spell alike, `if`,
`for`, `set`, whitespace control, inheritance, `include`, macros,
`import` and autoescaping.  Each case below is a template, a context
and any other templates it reaches; the script renders it with Jinja2
and writes the answer into the Novo test as the expected text, so the
expected text is never typed by hand.

Jinja2 is run the way Tera behaves where the two differ in a setting:

  * an unknown name is an error (`StrictUndefined`), as in Tera;
  * the template's last newline is kept (`keep_trailing_newline`);
  * autoescaping is decided by the name's suffix, `.html`, `.htm`,
    `.xml` and `.xhtml`, which is Tera's rule.

Jinja2 writes a quote as `&#34;` where html-nv writes `&quot;`.  Both
are valid HTML; the script rewrites Jinja2's spelling to html-nv's
before it writes the expectation, and that rewrite is the only one.

Constructs the two languages spell differently, or that only Tera has,
are not here.  They are tested by hand in `tests/lang_tests.nv` and `tests/filter_tests.nv`, each
with the rule it follows next to it.

Usage:  python tools/oracle.py > tests/oracle_tests.nv && novo fmt tests/oracle_tests.nv
        (needs the `jinja2` package)
"""
import json
import sys

import jinja2


def autoescape(name):
    return name is not None and name.endswith((".html", ".htm", ".xml", ".xhtml"))


def render(name, files):
    env = jinja2.Environment(
        loader=jinja2.DictLoader(files),
        undefined=jinja2.StrictUndefined,
        keep_trailing_newline=True,
        autoescape=autoescape,
    )
    return env.get_template(name).render(CTX)


CTX = {}

# Each group is a list of cases: (label, template, context, other files).
# A case whose last field is a string starting with "!" must fail, and
# the text after it is the Novo error kind the test expects.
GROUPS = []


def group(name, *cases):
    GROUPS.append((name, cases))


def c(label, template, ctx=None, files=None, name="page.html"):
    return dict(label=label, template=template, ctx=ctx or {}, files=files or {}, name=name)


def bad(label, kind, template, ctx=None, files=None, name="page.html"):
    d = c(label, template, ctx, files, name)
    d["error"] = kind
    return d


USER = {"name": "Ada", "tags": ["x", "y"], "address": {"city": "Oslo"}}

group(
    "output",
    c("plain text is copied", "just text\n"),
    c("a string", "{{ x }}", {"x": "hello"}),
    c("an int", "{{ n }}", {"n": 3}),
    c("a negative int", "{{ n }}", {"n": -7}),
    c("a whole float keeps its point", "{{ f }}", {"f": 3.0}),
    c("a float", "{{ f }}", {"f": 0.1}),
    c("another float", "{{ f }}", {"f": 2.5}),
    c("a dotted path", "{{ u.name }} {{ u.address.city }}", {"u": USER}),
    c("a list index with a dot", "{{ u.tags.1 }}", {"u": USER}),
    c("a list index with brackets", "{{ xs[0] }}{{ xs[1] }}", {"xs": [4, 5]}),
    c("a map key with brackets", "{{ u['name'] }}", {"u": USER}),
    c("a key from a variable", "{{ u[k] }}", {"u": USER, "k": "name"}),
    c("two expressions and text between", "<{{ a }}|{{ b }}>", {"a": 1, "b": "two"}),
    c("a string literal", "{{ 'it' }} {{ \"is\" }}"),
    c("an escaped quote in a literal", "{{ 'a\\'b' }}"),
    c("a number literal", "{{ 42 }} {{ 1.5 }}"),
    c("a negative literal", "{{ -3 }}"),
    c("a non-ASCII string", "{{ x }}", {"x": "héllo ✓"}),
    c("a comment", "a{# gone #}b"),
    c("a multi-line comment", "a{# one\ntwo #}b"),
    c("a brace that is not a tag", "{ x } { % } {"),
    c("a closing brace pair inside a string", "{{ '}}' }}"),
    bad("an unknown variable", "ErrorUnknownVariable", "{{ missing }}"),
    bad("an unknown field", "ErrorNoSuchField", "{{ u.nope }}", {"u": USER}),
    bad("an index past the end", "ErrorNoSuchField", "{{ xs.5 }}", {"xs": [1]}),
)

group(
    "autoescape",
    c("a script in an html template", "<p>{{ x }}</p>", {"x": "<script>alert(1)</script>"}),
    c("every one of the five characters", "{{ x }}", {"x": "a&b<c>d\"e'f"}),
    c("an attribute value", "<a title=\"{{ x }}\">t</a>", {"x": "say \"hi\""}),
    c("safe turns it off for the value", "{{ x | safe }}", {"x": "<b>bold</b>"}),
    c("safe is for that value only", "{{ x | safe }}{{ x }}", {"x": "<b>"}),
    c("escape is not applied twice", "{{ x | escape }}", {"x": "<b>"}),
    c("a text template is not escaped", "{{ x }}", {"x": "<b> & co"}, name="page.txt"),
    c("an xml template is escaped", "{{ x }}", {"x": "<b>"}, name="feed.xml"),
    c("an htm template is escaped", "{{ x }}", {"x": "<b>"}, name="page.htm"),
    c("a number is not touched", "{{ n }}", {"n": 5}),
    c("text outside a tag is not escaped", "<b>{{ x }}</b>", {"x": "a"}),
    c(
        "a macro's result is markup already",
        "{% macro b(t) %}<b>{{ t }}</b>{% endmacro %}{{ b('x<y') }}",
    ),
    c(
        "an included template is escaped like its parent",
        "{% include 'part.html' %}",
        {"x": "<i>"},
        {"part.html": "[{{ x }}]"},
    ),
    c("a loop item is escaped", "{% for x in xs %}{{ x }}{% endfor %}", {"xs": ["<a>", "b&"]}),
)

group(
    "conditions",
    c("if true", "{% if x %}y{% endif %}", {"x": True}),
    c("if false", "{% if x %}y{% endif %}", {"x": False}),
    c("if else", "{% if x %}y{% else %}n{% endif %}", {"x": 0}),
    c("elif", "{% if n == 1 %}a{% elif n == 2 %}b{% elif n == 3 %}c{% else %}d{% endif %}", {"n": 2}),
    c("the else after elifs", "{% if n == 1 %}a{% elif n == 2 %}b{% else %}d{% endif %}", {"n": 9}),
    c("zero is false", "{% if n %}t{% else %}f{% endif %}", {"n": 0}),
    c("zero point zero is false", "{% if n %}t{% else %}f{% endif %}", {"n": 0.0}),
    c("the empty string is false", "{% if s %}t{% else %}f{% endif %}", {"s": ""}),
    c("an empty list is false", "{% if s %}t{% else %}f{% endif %}", {"s": []}),
    c("an empty map is false", "{% if s %}t{% else %}f{% endif %}", {"s": {}}),
    c("a one-item list is true", "{% if s %}t{% else %}f{% endif %}", {"s": [0]}),
    c("a string is true", "{% if s %}t{% else %}f{% endif %}", {"s": "0"}),
    c("null is false", "{% if s %}t{% else %}f{% endif %}", {"s": None}),
    c("not", "{% if not x %}t{% else %}f{% endif %}", {"x": 0}),
    c("and", "{% if a and b %}t{% else %}f{% endif %}", {"a": 1, "b": 0}),
    c("or", "{% if a or b %}t{% else %}f{% endif %}", {"a": 0, "b": 1}),
    c("and binds tighter than or", "{% if a or b and c %}t{% else %}f{% endif %}", {"a": 1, "b": 0, "c": 0}),
    c("not binds tighter than and", "{% if not a and b %}t{% else %}f{% endif %}", {"a": 0, "b": 1}),
    c("parentheses", "{% if (a or b) and c %}t{% else %}f{% endif %}", {"a": 1, "b": 0, "c": 0}),
    c("equal ints", "{% if a == b %}t{% else %}f{% endif %}", {"a": 2, "b": 2}),
    c("an int equals the same float", "{% if a == b %}t{% else %}f{% endif %}", {"a": 1, "b": 1.0}),
    c("unequal", "{% if a != b %}t{% else %}f{% endif %}", {"a": "x", "b": "y"}),
    c("less", "{% if a < b %}t{% else %}f{% endif %}", {"a": 1, "b": 2}),
    c("less or equal", "{% if a <= b %}t{% else %}f{% endif %}", {"a": 2, "b": 2}),
    c("greater", "{% if a > b %}t{% else %}f{% endif %}", {"a": 3, "b": 2}),
    c("greater or equal", "{% if a >= b %}t{% else %}f{% endif %}", {"a": 1, "b": 2}),
    c("a string orders as bytes", "{% if a < b %}t{% else %}f{% endif %}", {"a": "apple", "b": "banana"}),
    c("an int against a float", "{% if a < b %}t{% else %}f{% endif %}", {"a": 1, "b": 1.5}),
    c("in a list", "{% if 2 in xs %}t{% else %}f{% endif %}", {"xs": [1, 2]}),
    c("not in a list", "{% if 5 not in xs %}t{% else %}f{% endif %}", {"xs": [1, 2]}),
    c("in a string", "{% if 'ell' in s %}t{% else %}f{% endif %}", {"s": "hello"}),
    c("in a map is a key", "{% if 'name' in u %}t{% else %}f{% endif %}", {"u": USER}),
    c("a list equals a list", "{% if a == b %}t{% else %}f{% endif %}", {"a": [1, 2], "b": [1, 2]}),
    c("a list is not another order", "{% if a == b %}t{% else %}f{% endif %}", {"a": [1, 2], "b": [2, 1]}),
    c("a map equals a map in another order", "{% if a == b %}t{% else %}f{% endif %}",
      {"a": {"x": 1, "y": 2}, "b": {"y": 2, "x": 1}}),
    c("nested ifs", "{% if a %}{% if b %}ab{% else %}a{% endif %}{% else %}none{% endif %}", {"a": 1, "b": 0}),
    c("a filter inside a condition", "{% if xs | length > 1 %}many{% else %}few{% endif %}", {"xs": [1, 2]}),
    bad("comparing a string with an int", "ErrorFilterRefused", "{% if a < b %}t{% endif %}", {"a": "x", "b": 1}),
)

group(
    "tests",
    c("defined", "{% if x is defined %}t{% else %}f{% endif %}", {"x": 1}),
    c("not defined", "{% if y is defined %}t{% else %}f{% endif %}"),
    c("undefined", "{% if y is undefined %}t{% else %}f{% endif %}"),
    c("is not defined", "{% if y is not defined %}t{% else %}f{% endif %}"),
    c("defined on a missing field", "{% if u.nick is defined %}t{% else %}f{% endif %}", {"u": USER}),
    c("string", "{% if x is string %}t{% else %}f{% endif %}", {"x": "a"}),
    c("not a string", "{% if x is string %}t{% else %}f{% endif %}", {"x": 1}),
    c("number", "{% if x is number %}t{% else %}f{% endif %}", {"x": 1.5}),
    c("an int is a number", "{% if x is number %}t{% else %}f{% endif %}", {"x": 2}),
    c("odd", "{% if x is odd %}t{% else %}f{% endif %}", {"x": 3}),
    c("even", "{% if x is even %}t{% else %}f{% endif %}", {"x": 3}),
    c("divisibleby", "{% if x is divisibleby(3) %}t{% else %}f{% endif %}", {"x": 9}),
    c("not divisibleby", "{% if x is divisibleby(4) %}t{% else %}f{% endif %}", {"x": 9}),
)

group(
    "loops",
    c("the body once per item", "{% for x in xs %}{{ x }}{% endfor %}", {"xs": ["a", "b", "c"]}),
    c("text between", "{% for x in xs %}<{{ x }}>{% endfor %}", {"xs": [1, 2]}),
    c("loop.index", "{% for x in xs %}{{ loop.index }}{% endfor %}", {"xs": ["a", "b", "c"]}),
    c("loop.index0", "{% for x in xs %}{{ loop.index0 }}{% endfor %}", {"xs": ["a", "b", "c"]}),
    c("loop.first", "{% for x in xs %}{% if loop.first %}F{% endif %}{{ x }}{% endfor %}", {"xs": [1, 2]}),
    c("loop.last", "{% for x in xs %}{{ x }}{% if not loop.last %},{% endif %}{% endfor %}", {"xs": [1, 2, 3]}),
    c("loop.length", "{% for x in xs %}{{ loop.length }}{% endfor %}", {"xs": [1, 2]}),
    c("an empty list takes the else", "{% for x in xs %}a{% else %}none{% endfor %}", {"xs": []}),
    c("a full list skips the else", "{% for x in xs %}a{% else %}none{% endfor %}", {"xs": [1]}),
    c("nested loops", "{% for a in xs %}{% for b in ys %}{{ a }}{{ b }} {% endfor %}{% endfor %}",
      {"xs": [1, 2], "ys": ["x", "y"]}),
    c("the inner loop variable is its own", "{% for a in xs %}{% for b in ys %}{{ loop.index }}{% endfor %}{{ loop.index }}{% endfor %}",
      {"xs": [1, 2], "ys": [1, 2, 3]}),
    c("a loop over a string", "{% for ch in s %}[{{ ch }}]{% endfor %}", {"s": "héy"}),
    c("a loop over a filtered list", "{% for x in xs | reverse %}{{ x }}{% endfor %}", {"xs": [1, 2, 3]}),
    c("a variable set before the loop is seen inside", "{% set p = '>' %}{% for x in xs %}{{ p }}{{ x }}{% endfor %}", {"xs": [1, 2]}),
    c("a set inside the loop ends with it",
      "{% for x in xs %}{% set y = x %}{{ y }}{% endfor %}{% if y is defined %}leak{% else %}ok{% endif %}", {"xs": [1, 2]}),
    c("a loop variable hides an outer one", "{% for x in xs %}{{ x }}{% endfor %}{{ x }}", {"xs": [1, 2], "x": "out"}),
    c("a loop over a list of maps", "{% for u in us %}{{ u.name }};{% endfor %}", {"us": [USER, {"name": "Bo"}]}),
    bad("a loop over a number", "ErrorFilterRefused", "{% for x in n %}{% endfor %}", {"n": 3}),
)

group(
    "set",
    c("a number", "{% set n = 2 %}{{ n }}"),
    c("a string", "{% set s = 'hi' %}{{ s }}"),
    c("from a variable", "{% set y = x %}{{ y }}", {"x": "v"}),
    c("from a filter", "{% set y = x | upper %}{{ y }}", {"x": "v"}),
    c("rebinding", "{% set n = 1 %}{% set n = 2 %}{{ n }}"),
    c("from a path", "{% set c = u.address.city %}{{ c }}", {"u": USER}),
    c("a list literal", "{% set xs = [1, 2, 3] %}{% for x in xs %}{{ x }}{% endfor %}"),
    c("a condition", "{% if n > 1 %}{% set m = 'big' %}{{ m }}{% endif %}", {"n": 2}),
)

group(
    "raw",
    c("raw keeps a variable", "{% raw %}{{ x }}{% endraw %}", {"x": 1}),
    c("raw keeps a tag", "{% raw %}{% if x %}{% endraw %}"),
    c("raw around other text", "a{% raw %} {{ b }} {% endraw %}c"),
    c("raw with a comment opener", "{% raw %}{# kept #}{% endraw %}"),
)

group(
    "whitespace",
    c("dash on a tag's left strips the text before", "a  \n  {%- if x %}b{% endif %}", {"x": 1}),
    c("dash on a tag's right strips the text after", "{% if x -%}  \n  b{% endif %}", {"x": 1}),
    c("both sides", "a \n{%- if x -%}\n b \n{%- endif -%}\n c", {"x": 1}),
    c("dash on an expression", "a  {{- x -}}  b", {"x": 1}),
    c("dash on a comment", "a  {#- gone -#}  b"),
    c("newlines are kept without a dash", "a\n{% if x %}\nb\n{% endif %}\nc", {"x": 1}),
    c("a loop that keeps its lines", "{% for x in xs %}\n- {{ x }}\n{% endfor %}", {"xs": [1, 2]}),
    c("a loop that strips its lines", "{% for x in xs -%}\n- {{ x }}\n{%- endfor %}", {"xs": [1, 2]}),
    c("a trailing newline is kept", "a\n"),
    c("raw with dashes", "a  {%- raw -%}  {{ x }}  {%- endraw -%}  b"),
)

group(
    "filters",
    c("upper", "{{ x | upper }}", {"x": "hello"}),
    c("lower", "{{ x | lower }}", {"x": "HeLLo"}),
    c("capitalize", "{{ x | capitalize }}", {"x": "hELLO wORLD"}),
    c("title", "{{ x | title }}", {"x": "hello wORLD-foo"}),
    c("trim", "[{{ x | trim }}]", {"x": "  a b \n"}),
    c("length of a string counts characters", "{{ x | length }}", {"x": "héllo"}),
    c("length of a list", "{{ x | length }}", {"x": [1, 2, 3]}),
    c("length of a map", "{{ x | length }}", {"x": {"a": 1, "b": 2}}),
    c("wordcount", "{{ x | wordcount }}", {"x": "one two  three\nfour"}),
    c("replace", "{{ x | replace('a', 'o') }}", {"x": "banana"}),
    c("replace with a longer text", "{{ x | replace('an', 'ANT') }}", {"x": "banana"}),
    c("indent", "{{ x | indent(2) }}", {"x": "a\nb\n\nc"}, name="page.txt"),
    c("indent with a trailing newline", "{{ x | indent(4) }}", {"x": "a\nb\n"}, name="page.txt"),
    c("striptags", "{{ x | striptags }}", {"x": "<b>bold</b> and <i>it</i>"}, name="page.txt"),
    c("first", "{{ x | first }}", {"x": [7, 8]}),
    c("last", "{{ x | last }}", {"x": [7, 8]}),
    c("first of a string", "{{ x | first }}", {"x": "héy"}),
    c("last of a string", "{{ x | last }}", {"x": "hey"}),
    c("reverse a list", "{{ x | reverse | join(',') }}", {"x": [1, 2, 3]}),
    c("reverse a string", "{{ x | reverse }}", {"x": "abc"}),
    c("join", "{{ x | join(', ') }}", {"x": ["a", "b", "c"]}),
    c("join without a separator", "{{ x | join }}", {"x": ["a", "b"]}),
    c("join numbers", "{{ x | join('-') }}", {"x": [1, 2, 3]}),
    c("sort numbers", "{{ x | sort | join(',') }}", {"x": [3, 1, 2]}),
    c("sort floats and ints", "{{ x | sort | join(',') }}", {"x": [2, 1.5, 1]}),
    c("sort words", "{{ x | sort | join(',') }}", {"x": ["pear", "apple", "fig"]}),
    c("sort by a field", "{{ x | sort(attribute='n') | map(attribute='s') | join(',') }}",
      {"x": [{"n": 2, "s": "b"}, {"n": 1, "s": "a"}, {"n": 3, "s": "c"}]}),
    c("sort keeps equal items in order", "{{ x | sort(attribute='n') | map(attribute='s') | join(',') }}",
      {"x": [{"n": 1, "s": "a"}, {"n": 0, "s": "z"}, {"n": 1, "s": "b"}]}),
    c("unique", "{{ x | unique | join(',') }}", {"x": [1, 2, 1, 3, 2]}),
    c("unique words", "{{ x | unique | join(',') }}", {"x": ["a", "b", "a"]}),
    c("map a field", "{{ x | map(attribute='n') | join(',') }}", {"x": [{"n": 1}, {"n": 2}]}),
    c("abs of an int", "{{ x | abs }}", {"x": -5}),
    c("abs of a float", "{{ x | abs }}", {"x": -2.5}),
    c("round a float", "{{ x | round }}", {"x": 3.7}),
    c("round down", "{{ x | round }}", {"x": 3.2}),
    c("round to places", "{{ x | round(2) }}", {"x": 3.14159}),
    c("round a negative", "{{ x | round }}", {"x": -3.7}),
    c("round an int", "{{ x | round }}", {"x": 5}),
    c("int of a float", "{{ x | int }}", {"x": 3.9}),
    c("int of a negative float", "{{ x | int }}", {"x": -3.9}),
    c("int of a string", "{{ x | int }}", {"x": "42"}),
    c("int of text with a fraction", "{{ x | int }}", {"x": "3.7"}),
    c("int of words", "{{ x | int }}", {"x": "abc"}),
    c("int of words with a default", "{{ x | int(5) }}", {"x": "abc"}),
    c("float of an int", "{{ x | float }}", {"x": 3}),
    c("float of a string", "{{ x | float }}", {"x": "2.5"}),
    c("filesizeformat zero", "{{ x | filesizeformat }}", {"x": 0}),
    c("filesizeformat one", "{{ x | filesizeformat }}", {"x": 1}),
    c("filesizeformat bytes", "{{ x | filesizeformat }}", {"x": 999}),
    c("filesizeformat a thousand", "{{ x | filesizeformat }}", {"x": 1000}),
    c("filesizeformat megabytes", "{{ x | filesizeformat }}", {"x": 1500000}),
    c("filesizeformat gigabytes", "{{ x | filesizeformat }}", {"x": 123456789012}),
    c("urlencode", "{{ x | urlencode }}", {"x": "a b/c?d=é"}, name="page.txt"),
    c("escape", "{{ x | escape }}", {"x": "<a href=\"x\">"}, name="page.txt"),
    c("default on a missing name", "{{ y | default('-') }}"),
    c("default on a missing field", "{{ u.nick | default('anon') }}", {"u": USER}),
    c("default leaves a value alone", "{{ x | default('-') }}", {"x": "set"}),
    c("default does not replace an empty string", "[{{ x | default('-') }}]", {"x": ""}),
    c("default with true replaces a false value", "[{{ x | default('-', true) }}]", {"x": ""}),
    c("default leaves zero alone", "{{ x | default('-') }}", {"x": 0}),
    c("a chain", "{{ x | trim | upper | replace('A', 'a') }}", {"x": "  banana "}),
    c("a filter on a literal", "{{ 'abc' | upper }}"),
    c("a filter on a path", "{{ u.name | lower }}", {"u": USER}),
    c("a filter with an argument from a variable", "{{ x | join(sep) }}", {"x": [1, 2], "sep": "+"}),
    c("a filter binds tighter than a comparison", "{% if x | length == 3 %}t{% else %}f{% endif %}", {"x": "abc"}),
    c("filter block", "{% filter upper %}hello {{ x }}{% endfilter %}", {"x": "there"}),
    bad("an unknown filter", "ErrorUnknownFilter", "{{ x | nofilter }}", {"x": 1}),
)

group(
    "inheritance",
    c(
        "a child fills a block",
        "{% extends 'base.html' %}{% block content %}child{% endblock %}",
        files={"base.html": "<main>{% block content %}base{% endblock %}</main>"},
    ),
    c(
        "a block the child leaves alone keeps the parent's text",
        "{% extends 'base.html' %}",
        files={"base.html": "<main>{% block content %}base{% endblock %}</main>"},
    ),
    c(
        "text outside the child's blocks is dropped",
        "{% extends 'base.html' %}ignored{% block content %}child{% endblock %}ignored",
        files={"base.html": "[{% block content %}{% endblock %}]"},
    ),
    c(
        "super",
        "{% extends 'base.html' %}{% block content %}{{ super() }}+child{% endblock %}",
        files={"base.html": "{% block content %}base{% endblock %}"},
    ),
    c(
        "super twice in a row",
        "{% extends 'base.html' %}{% block content %}{{ super() }}{{ super() }}{% endblock %}",
        files={"base.html": "{% block content %}b{% endblock %}"},
    ),
    c(
        "two blocks",
        "{% extends 'base.html' %}{% block a %}A{% endblock %}{% block b %}B{% endblock %}",
        files={"base.html": "{% block a %}a{% endblock %}-{% block b %}b{% endblock %}"},
    ),
    c(
        "three levels, the nearest wins",
        "{% extends 'mid.html' %}{% block x %}top{% endblock %}",
        files={
            "mid.html": "{% extends 'root.html' %}{% block x %}mid{% endblock %}",
            "root.html": "<{% block x %}root{% endblock %}>",
        },
    ),
    c(
        "three levels, super goes up one at a time",
        "{% extends 'mid.html' %}{% block x %}{{ super() }}+top{% endblock %}",
        files={
            "mid.html": "{% extends 'root.html' %}{% block x %}{{ super() }}+mid{% endblock %}",
            "root.html": "<{% block x %}root{% endblock %}>",
        },
    ),
    c(
        "three levels, a middle level that does not override",
        "{% extends 'mid.html' %}{% block x %}{{ super() }}+top{% endblock %}",
        files={
            "mid.html": "{% extends 'root.html' %}",
            "root.html": "<{% block x %}root{% endblock %}>",
        },
    ),
    c(
        "a block inside a block",
        "{% extends 'base.html' %}{% block inner %}INNER{% endblock %}",
        files={"base.html": "{% block outer %}[{% block inner %}in{% endblock %}]{% endblock %}"},
    ),
    c(
        "a child overrides the outer block and the inner one stays",
        "{% extends 'base.html' %}{% block outer %}<{% block inner %}new{% endblock %}>{% endblock %}",
        files={"base.html": "{% block outer %}[{% block inner %}in{% endblock %}]{% endblock %}"},
    ),
    c(
        "the context reaches the blocks",
        "{% extends 'base.html' %}{% block content %}{{ title }}{% endblock %}",
        {"title": "Home"},
        {"base.html": "{% block content %}{% endblock %}"},
    ),
    c(
        "the parent's own variables",
        "{% extends 'base.html' %}",
        {"site": "S"},
        {"base.html": "{{ site }}:{% block content %}{% endblock %}"},
    ),
    c(
        "a block named with the end name",
        "{% extends 'base.html' %}{% block content %}c{% endblock content %}",
        files={"base.html": "{% block content %}b{% endblock content %}"},
    ),
    bad("extending a template that is not there", "ErrorTemplateNotFound", "{% extends 'nowhere.html' %}"),
    bad("a block defined twice", "ErrorDuplicateBlock", "{% block a %}{% endblock %}{% block a %}{% endblock %}"),
)

group(
    "include",
    c("an include", "a{% include 'part.html' %}b", files={"part.html": "[part]"}),
    c("an include sees the context", "{% include 'part.html' %}", {"x": 5}, {"part.html": "x={{ x }}"}),
    c("an include sees the loop variable", "{% for x in xs %}{% include 'part.html' %}{% endfor %}", {"xs": [1, 2]},
      {"part.html": "<{{ x }}>"}),
    c("an include sees a set variable", "{% set v = 'S' %}{% include 'part.html' %}", files={"part.html": "{{ v }}"}),
    c("an include that includes", "{% include 'a.html' %}", files={"a.html": "a({% include 'b.html' %})", "b.html": "b"}),
    c("an include of a computed name", "{% include name %}", {"name": "part.html"}, {"part.html": "computed"}),
    c("an include of a template that extends", "{% include 'child.html' %}",
      files={"child.html": "{% extends 'base.html' %}{% block c %}C{% endblock %}", "base.html": "<{% block c %}{% endblock %}>"}),
    c("an include inside a block", "{% extends 'base.html' %}{% block c %}{% include 'part.html' %}{% endblock %}",
      files={"base.html": "<{% block c %}{% endblock %}>", "part.html": "P"}),
    c("an include inside an if", "{% if x %}{% include 'part.html' %}{% endif %}", {"x": 1}, {"part.html": "P"}),
    bad("an include that is not there", "ErrorTemplateNotFound", "{% include 'nowhere.html' %}"),
    bad("an include that includes itself", "ErrorCycle", "{% include 'page.html' %}"),
)

group(
    "macros",
    c("a macro", "{% macro hi(n) %}Hello {{ n }}{% endmacro %}{{ hi('Ada') }}"),
    c("two arguments", "{% macro add(a, b) %}{{ a }}+{{ b }}{% endmacro %}{{ add(1, 2) }}"),
    c("a default", "{% macro hi(n='you') %}Hello {{ n }}{% endmacro %}{{ hi() }}"),
    c("a default overridden", "{% macro hi(n='you') %}Hello {{ n }}{% endmacro %}{{ hi('Ada') }}"),
    c("a keyword argument", "{% macro hi(a, b) %}{{ a }}{{ b }}{% endmacro %}{{ hi(b='B', a='A') }}"),
    c("a macro called twice", "{% macro b(t) %}<{{ t }}>{% endmacro %}{{ b(1) }}{{ b(2) }}"),
    c("a macro in a loop", "{% macro b(t) %}<{{ t }}>{% endmacro %}{% for x in xs %}{{ b(x) }}{% endfor %}", {"xs": [1, 2]}),
    c("a macro calling a macro",
      "{% macro a() %}A{{ b() }}{% endmacro %}{% macro b() %}B{% endmacro %}{{ a() }}"),
    c("a macro that loops",
      "{% macro l(xs) %}{% for x in xs %}{{ x }}{% endfor %}{% endmacro %}{{ l([1, 2, 3]) }}"),
    c("an imported macro", "{% import 'm.html' as m %}{{ m.hi('Ada') }}",
      files={"m.html": "{% macro hi(n) %}Hi {{ n }}{% endmacro %}"}),
    c("two imported macros", "{% import 'm.html' as m %}{{ m.a() }}{{ m.b() }}",
      files={"m.html": "{% macro a() %}A{% endmacro %}{% macro b() %}B{% endmacro %}"}),
    c("an import under two names", "{% import 'm.html' as x %}{% import 'm.html' as y %}{{ x.a() }}{{ y.a() }}",
      files={"m.html": "{% macro a() %}A{% endmacro %}"}),
    c("an imported macro uses its own file's macros", "{% import 'm.html' as m %}{{ m.a() }}",
      files={"m.html": "{% macro a() %}[{{ b() }}]{% endmacro %}{% macro b() %}B{% endmacro %}"}),
    c("an import in a child's block",
      "{% extends 'base.html' %}{% import 'm.html' as m %}{% block c %}{{ m.a() }}{% endblock %}",
      files={"base.html": "<{% block c %}{% endblock %}>", "m.html": "{% macro a() %}A{% endmacro %}"}),
    c("a macro result goes through a filter", "{% macro m() %}ab{% endmacro %}{{ m() | upper }}"),
    bad("a macro that is not there", "ErrorNoSuchField", "{% import 'm.html' as m %}{{ m.nope() }}", files={"m.html": ""}),
    bad("an import that is not there", "ErrorTemplateNotFound", "{% import 'nowhere.html' as m %}{{ m.a() }}"),
)

# ── Values: JSON text, compared with Python's own encoder ─────────────

JSON_VALUES = [
    ("null", None),
    ("true", True),
    ("false", False),
    ("an int", 42),
    ("a negative int", -7),
    ("a float", 2.5),
    ("a whole float", 3.0),
    ("a string", "hello"),
    ("quotes and a backslash", 'a"b\\c'),
    ("control characters", "a\nb\tc\rd\u0001e"),
    ("non-ASCII text", "héllo ✓"),
    ("an empty list", []),
    ("a list", [1, "a", None, 2.5]),
    ("an empty map", {}),
    ("a map", {"a": 1, "b": [True, None]}),
    ("a nested value", {"u": {"tags": ["x", {"y": 1}]}, "n": -1}),
]


def nv_str(s):
    out = []
    for ch in s:
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "$":
            out.append("\\$")
        elif ord(ch) < 32:
            out.append("\\u{%x}" % ord(ch))
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


def nv_value(v):
    if v is None:
        return "ValueNull"
    if v is True or v is False:
        return "ValueBool(%s)" % ("true" if v else "false")
    if isinstance(v, int):
        return "ValueInt(%d)" % v
    if isinstance(v, float):
        return "ValueFloat(%r)" % v
    if isinstance(v, str):
        return "ValueStr(%s)" % nv_str(v)
    if isinstance(v, list):
        return "ValueList([%s])" % ", ".join(nv_value(x) for x in v)
    return "ValueMap([%s])" % ", ".join(
        "TeraPair { key: %s, value: %s }" % (nv_str(k), nv_value(x)) for k, x in v.items()
    )


def nv_ctx(ctx):
    return "ctx_of(%s)" % nv_value(ctx)


def nv_files(case):
    files = dict(case["files"])
    files[case["name"]] = case["template"]
    return "[%s]" % ", ".join(
        "TeraSource { name: %s, text: %s }" % (nv_str(k), nv_str(v)) for k, v in files.items()
    )


def func_name(s):
    return "test_oracle_" + "".join(ch if ch.isalnum() else "_" for ch in s)


def main():
    out = sys.stdout.write
    out(HEADER)
    total = 0
    for gname, cases in GROUPS:
        out("\n@test\nfn %s() [io]\n" % func_name(gname))
        for cs in cases:
            files = dict(cs["files"])
            files[cs["name"]] = cs["template"]
            out("    test.case(%s)\n" % nv_str(cs["label"]))
            CTX.clear()
            CTX.update(cs["ctx"])
            if "error" in cs:
                try:
                    render(cs["name"], files)
                except Exception:
                    pass
                else:
                    raise SystemExit("Jinja2 accepted %r" % cs["label"])
                out("    expect_error(%s, %s, %s, %s)\n" % (
                    nv_files(cs), nv_str(cs["name"]), nv_ctx(cs["ctx"]), nv_str(cs["error"])))
            else:
                CTX.clear()
                CTX.update(cs["ctx"])
                want = render(cs["name"], files).replace("&#34;", "&quot;")
                out("    expect(%s, %s, %s, %s)\n" % (
                    nv_files(cs), nv_str(cs["name"]), nv_ctx(cs["ctx"]), nv_str(want)))
            total += 1
    out("\n@test\nfn test_oracle_json_text() [io]\n")
    for label, v in JSON_VALUES:
        want = json.dumps(v, separators=(",", ":"), ensure_ascii=False)
        out("    test.case(%s)\n" % nv_str("to_json of " + label))
        out("    test.assert(teraval.to_json(%s) == %s)\n" % (nv_value(v), nv_str(want)))
        total += 1
    sys.stderr.write("%d cases\n" % total)


HEADER = '''// oracle_tests.nv — cases whose expected text came from Jinja2.
//
// Generated by tools/oracle.py; do not edit by hand.  Each case is a
// template, a context and any other templates it reaches, and the
// expected text is what Jinja2 3.1 renders for it, run the way Tera
// behaves where the two differ (an unknown name is an error, the last
// newline is kept, the name's suffix decides autoescaping).  Jinja2
// spells a quote `&#34;`; the generator writes html-nv's `&quot;`.
//
// The last test compares `teraval.to_json` with Python's `json.dumps`
// in its compact form.

use std.test
use teraval
use teraparse
use terarender
use teraerror

fn ctx_of(v: teraval.TeraValue) -> teraval.TeraContext
    match teraval.context_from_map(v)
        Some(c) =>
            c
        None    =>
            teraval.context_new()

fn set_of(files: [teraerror.TeraSource]) -> teraparse.TeraSet [io]
    var s = teraparse.set_new()
    for f in files
        match teraparse.set_add(s, f.name, f.text)
            Ok(next) =>
                s = next
            Err(_)   =>
                continue
    s

fn expect(files: [teraerror.TeraSource], name: Str, ctx: teraval.TeraContext, want: Str) [io]
    match terarender.render_str(set_of(files), name, ctx)
        Ok(got) =>
            test.assert(got == want)
        Err(e)  =>
            println(teraerror.one_line(e))
            test.assert(false)

fn kind_of(e: teraerror.TeraError) -> Str
    match e.kind
        ErrorSyntax(_)          =>
            "ErrorSyntax"
        ErrorUnclosed(_)        =>
            "ErrorUnclosed"
        ErrorUnexpectedTag(_)   =>
            "ErrorUnexpectedTag"
        ErrorUnknownVariable(_) =>
            "ErrorUnknownVariable"
        ErrorNoSuchField(_)     =>
            "ErrorNoSuchField"
        ErrorUnknownFilter(_, _) =>
            "ErrorUnknownFilter"
        ErrorFilterRefused(_, _) =>
            "ErrorFilterRefused"
        ErrorTemplateNotFound(_) =>
            "ErrorTemplateNotFound"
        ErrorCycle(_)           =>
            "ErrorCycle"
        ErrorDuplicateBlock(_)  =>
            "ErrorDuplicateBlock"
        ErrorLimit(_)           =>
            "ErrorLimit"

// A template that parses into the set but fails to render, or one that
// does not parse at all: either way the error's kind is what is asserted.
fn expect_error(files: [teraerror.TeraSource], name: Str, ctx: teraval.TeraContext, kind: Str) [io]
    var s = teraparse.set_new()
    for f in files
        match teraparse.set_add(s, f.name, f.text)
            Ok(next) =>
                s = next
            Err(e)   =>
                test.assert(kind_of(e) == kind)
                return
    match terarender.render_str(s, name, ctx)
        Ok(_)  =>
            test.assert(false)
        Err(e) =>
            test.assert(kind_of(e) == kind)
'''

main()
