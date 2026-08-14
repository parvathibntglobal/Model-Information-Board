"""RFC 9309 rule matching, because `urllib.robotparser` implements the 1996 draft.

`RobotFileParser` gets three things right that are tedious to rewrite: group
parsing with blank-line separation and comments, user-agent matching, and
`Crawl-delay`. It gets the actual allowance decision wrong, twice, and this
module replaces only that.

WHAT IT GETS WRONG
------------------
1. **No wildcards.** `RuleLine.applies_to` is
   `self.path == "*" or filename.startswith(self.path)`. RFC 9309 §2.2.3
   defines exactly three special characters — `#` for comments, `*` for zero
   or more of any character, `$` for end-of-pattern — and the stdlib supports
   none of them inside a path.

   Measured 2026-08-14 against the nine seeded feeds: `medium.com` disallows
   `/*/*source=` and every article link in a Medium feed carries
   `?source=rss----`, so **5 of 6 sampled Airbnb article URLs are permitted
   by our gate and forbidden by the host**. That is a rule we could not
   express being read as permission, which is rule 6 pointed outward.

2. **First match in file order, not most specific.** `Entry.allowance`
   returns on the first rule whose path prefixes the URL. RFC 9309 §2.2.2:
   *"The most specific match found MUST be used. The most specific match is
   the match that has the most octets."* and *"If an 'allow' rule and a
   'disallow' rule are equivalent, then the 'allow' rule SHOULD be used."*

   This one is prospective rather than remedial, and the measurement says so:
   **zero live disagreements across the nine feeds, two latent, and both erring
   toward refusal** —

       slack.engineering      Disallow: /wp-admin/  then  Allow: /wp-admin/admin-ajax.php
       engineering.atspotify  Disallow: /static/    then  Allow: /static/images/

   both of which we currently refuse and are in fact permitted. The dangerous
   ordering — `Allow: /` followed by a narrower `Disallow:` — appears in none
   of the nine, but it is a common idiom on the wider web and forty feeds will
   not stay this clean.

THE SAME RULE MEANS DIFFERENT THINGS ON TWO HOSTS
-------------------------------------------------
Worth knowing before reading `contract/sources.yaml`'s class B ruling.
`medium.com/robots.txt` and `netflixtechblog.com/robots.txt` are the same 37
rule lines, and `Disallow: /*/*source=` compiles to `^/.*/.*source=`, which
needs two slashes before `source=`:

    medium.com/airbnb-engineering/<slug>?source=…   two slashes   disallowed
    netflixtechblog.com/<slug>?source=…             one slash     NOT disallowed

A publication on `medium.com` is `/<publication>/<slug>`; a custom domain is
`/<slug>`. So on `netflixtechblog.com` the wildcard rule does not reach the
article paths at all, and only the 403 stops us there.

PERCENT-ENCODING, DOCUMENTED RATHER THAN SOLVED
-----------------------------------------------
`RuleLine.__init__` runs the declared path through `urllib.parse.quote`, so
`Disallow: /*/*source=` is stored as `/%2A/%2Asource%3D`. The wildcards
survive, encoded, so this module unquotes to recover the pattern.

**A robots.txt containing a literal `%2A` is therefore indistinguishable from
one containing `*`.** There is no clean resolution: by the time the rule
reaches us the two have the same representation, and reaching around
`RobotFileParser` to the raw bytes would mean reimplementing the group parsing
this module exists to avoid. The failure is a `%2A` read as a wildcard, which
is over-broad — it refuses more than the publisher wrote, not less — so the
ambiguity resolves in the safe direction. Recorded so the next reader does not
mistake it for an oversight.

Both sides are decoded before comparison, for the same reason: a pattern in
decoded space compared against a path in encoded space matches nothing.

WHAT IS DELIBERATELY NOT FIXED
------------------------------
Group selection. `can_fetch` takes the first named group whose user-agent
substring-matches, where RFC 9309 §2.2.1 asks for the most specific match.
Medium's file has one `*` group and one multi-agent group, so it does not
bite, and it is a separate argument from this one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit
from urllib.robotparser import Entry, RobotFileParser

#: A pattern with more wildcards than this is refused rather than compiled.
#: `^/.*/.*/.*/…` backtracks badly, and a robots.txt is attacker-adjacent
#: input in the sense that we do not control it. Twenty is far above anything
#: observed: the widest in the nine seeded feeds is two.
MAX_WILDCARDS = 20


@dataclass(frozen=True)
class Rule:
    """One `Allow:` or `Disallow:`, compiled if we could compile it."""

    allow: bool
    #: As the publisher wrote it, decoded. `''` means "every path" for Allow
    #: and, per RFC 9309 §2.2.2, "no constraint" for Disallow.
    pattern: str
    #: None when the pattern uses a construct we cannot evaluate.
    regex: re.Pattern[str] | None
    #: Everything before the first special construct. An unparsable rule
    #: cannot match outside this, which is what keeps fail-closed scoped to a
    #: path rather than silently widening to the whole host.
    literal_prefix: str
    #: Why it could not be compiled. None when it could.
    unparsable_because: str | None = None

    @property
    def parsable(self) -> bool:
        return self.regex is not None

    def matches(self, path: str) -> bool:
        return self.regex is not None and self.regex.match(path) is not None

    def could_reach(self, path: str) -> bool:
        """Might an unparsable rule cover this path? Bounded by its prefix.

        A malformed `/blog/<garbage>` cannot match anything outside `/blog/`,
        so refusing on it takes `/blog/*` offline and clears the rest. Without
        this bound, "fail closed for the path" collapses into fail closed for
        the host: an unevaluable rule has unknown extent, so every path looks
        like it might be covered.
        """
        return path.startswith(self.literal_prefix)


def compile_pattern(pattern: str, *, allow: bool) -> Rule:
    """Compile one rule path. Never raises — an uncompilable rule is a `Rule`.

    `*` becomes `.*` and a trailing `$` anchors the end. Everything else is
    escaped, because those are the only two constructs RFC 9309 defines.
    """
    literal_prefix = _literal_prefix(pattern)

    def refuse(reason: str) -> Rule:
        return Rule(allow, pattern, None, literal_prefix, reason)

    if pattern.count("*") > MAX_WILDCARDS:
        return refuse(
            f"{pattern.count('*')} wildcards exceeds the {MAX_WILDCARDS} limit"
        )

    anchored = pattern.endswith("$")
    body = pattern[:-1] if anchored else pattern
    if "$" in body:
        # RFC 9309 §2.2.3 defines `$` as "the end of the match pattern". A `$`
        # anywhere else is undefined, and guessing between "literal dollar" and
        # "the publisher meant an anchor" is exactly the guess this module
        # exists to stop making.
        return refuse("'$' appears before the end of the pattern, which RFC 9309 leaves undefined")

    try:
        compiled = re.compile(
            "^" + "".join(".*" if ch == "*" else re.escape(ch) for ch in body)
            + ("$" if anchored else "")
        )
    except re.error as exc:  # pragma: no cover - everything else is escaped
        return refuse(f"pattern did not compile: {exc}")

    return Rule(allow, pattern, compiled, literal_prefix)


def _literal_prefix(pattern: str) -> str:
    """The leading run that contains no special construct."""
    for index, ch in enumerate(pattern):
        if ch in "*$":
            return pattern[:index]
    return pattern


@dataclass(frozen=True)
class Allowance:
    """Whether one path may be fetched, and which rule decided it."""

    allowed: bool
    reason: str
    rule: Rule | None = None


def decide(rules: tuple[Rule, ...] | list[Rule], path: str) -> Allowance:
    """Apply one group's rules to one path, per RFC 9309 §2.2.2.

    Order of business:

      1. **An unparsable rule that could reach this path refuses it.** RFC
         9309 §2.2.4 is lenient here — crawlers *may* ignore records they do
         not understand — and we are deliberately stricter, the same way the
         gate is stricter than the RFC on 4xx. Absence of permission is not
         permission, and a rule we could not read is not a rule that said yes.
      2. Otherwise the most specific match wins: most octets of pattern.
      3. An `Allow` and a `Disallow` of equal length resolve to `Allow`.
      4. No rule matches, so nothing forbids it.
    """
    blocking = [
        rule for rule in rules if not rule.parsable and rule.could_reach(path)
    ]
    if blocking:
        rule = blocking[0]
        return Allowance(
            False,
            f"disallowed: a rule we could not evaluate covers this path — "
            f"{'Allow' if rule.allow else 'Disallow'}: {rule.pattern!r} "
            f"({rule.unparsable_because}). Refused for paths under "
            f"{rule.literal_prefix!r} only.",
            rule,
        )

    best: Rule | None = None
    for rule in rules:
        if not rule.matches(path):
            continue
        if best is None or len(rule.pattern) > len(best.pattern):
            best = rule
        elif len(rule.pattern) == len(best.pattern) and rule.allow and not best.allow:
            # RFC 9309 §2.2.2: "If an 'allow' rule and a 'disallow' rule are
            # equivalent, then the 'allow' rule SHOULD be used."
            best = rule

    if best is None:
        return Allowance(True, "allowed: no rule matches this path")
    verb = "Allow" if best.allow else "Disallow"
    return Allowance(
        best.allow,
        f"{'allowed' if best.allow else 'disallowed'} by the most specific "
        f"match, {verb}: {best.pattern!r}",
        best,
    )


def rules_from_entry(entry: Entry) -> tuple[Rule, ...]:
    """Recover compiled rules from a parsed group.

    `RuleLine.path` is percent-encoded by `RobotFileParser`, so it is decoded
    here — see the module docstring on the `%2A` ambiguity that creates.

    An empty `Disallow:` is dropped rather than compiled. `RuleLine.__init__`
    has already flipped it to `allowance=True`, and RFC 9309 §2.2.2 makes it a
    statement that nothing is forbidden — as a rule it would match every path
    at length zero and lose every specificity comparison anyway, but dropping
    it keeps `decide` honest about what actually constrained the answer.
    """
    rules = []
    for line in entry.rulelines:
        pattern = unquote(line.path)
        if pattern == "" and line.allowance:
            continue
        rules.append(compile_pattern(pattern, allow=line.allowance))
    return tuple(rules)


def applicable_entry(parser: RobotFileParser, user_agent: str) -> Entry | None:
    """The group whose rules bind us, mirroring `can_fetch`'s selection.

    Deliberately the same first-matching-group behaviour as the stdlib rather
    than RFC 9309 §2.2.1's most-specific-group. Changing it is a separate
    argument, and the observed files have one `*` group plus at most one named
    group, so the two agree today. See the module docstring.
    """
    for entry in parser.entries:
        if entry.applies_to(user_agent):
            return entry
    return parser.default_entry


def path_for_matching(url: str) -> str:
    """The part of a URL that rules are compared against, decoded.

    Query included, because that is where `?source=` lives and a rule like
    `/*/*source=` says nothing about a path without it. Fragment excluded: it
    never reaches the server.
    """
    parts = urlsplit(url)
    path = parts.path or "/"
    if parts.query:
        path = f"{path}?{parts.query}"
    return unquote(path)


def allowance_for(parser: RobotFileParser, user_agent: str, url: str) -> Allowance:
    """The whole decision for one URL: pick the group, apply its rules."""
    entry = applicable_entry(parser, user_agent)
    if entry is None:
        return Allowance(True, "no group in this robots.txt applies to our user-agent")
    return decide(rules_from_entry(entry), path_for_matching(url))
