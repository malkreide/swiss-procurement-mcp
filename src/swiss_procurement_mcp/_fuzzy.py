"""ARCH-003: widening a search term that found nothing — visibly.

An empty result is a bad answer when a slightly different term would have
worked. "Metallbauarbeiten" returning nothing while "Metall" returns forty CPV
codes is a failure of the lookup, not of the question.

The catch is that silent widening is worse than the empty result it replaces. If
the server quietly searches for something the caller did not ask about and
returns the hits as if they were the answer, a model will report them as such.
That is why every function here returns *what it searched for* alongside the
result, and why the tools that use it set `match_type="fuzzy"` and say in `note`
which term actually produced the hits.

**Only the taxonomy lookups use this.** Tender and award search stay exact-only,
deliberately — see `ARCH-003` in `SECURITY.md`. Widening a procurement query can
imply a tender exists when none does, and "no tender matched" is a legitimate,
actionable answer in a way that "no such CPV code" is not.

The widening itself is deliberately dumb, because the upstream code search is a
substring matcher and German compounds put the head at the front:
`Metallbauarbeiten` ⊃ `Metallbau` ⊃ `Metall`. Each shorter prefix matches a
superset of the longer one. No stemmer, no dictionary, nothing that could
silently mean something else in a language this server does not model.
"""

from __future__ import annotations

# Below this a prefix stops narrowing anything: "Met" matches half the taxonomy,
# and results the caller cannot connect to their question are noise wearing the
# costume of an answer.
MIN_TERM_LENGTH = 4

# Each candidate is one more upstream request on a path that has already failed
# once. Three is enough to get from a full compound to its head and cheap enough
# to spend on a query that would otherwise return nothing.
MAX_CANDIDATES = 3


def widen(query: str) -> list[str]:
    """Terms to try after `query` itself came back empty, best first.

    Two strategies, in order of how much they preserve the caller's intent:

    1. **Drop qualifiers.** For a multi-word query, the longest token is usually
       the subject and the rest are adjectives — "mobile Metallbauten" is asking
       about Metallbauten. Tried longest-first because a longer token carries
       more of the original question.
    2. **Shorten the compound.** For a single long word, progressively shorter
       prefixes. Only ever a prefix: an infix or a stem would need a model of
       German morphology, and guessing wrong invents a term the caller never
       used.

    Returns at most `MAX_CANDIDATES` entries, never including `query` itself and
    never duplicating.
    """
    query = query.strip()
    if not query:
        return []

    seen = {query.casefold()}
    out: list[str] = []

    def _add(term: str) -> None:
        if len(term) < MIN_TERM_LENGTH or term.casefold() in seen:
            return
        seen.add(term.casefold())
        out.append(term)

    tokens = query.split()
    if len(tokens) > 1:
        for token in sorted(tokens, key=len, reverse=True):
            _add(token)
            if len(out) >= MAX_CANDIDATES:
                return out

    # Applies to a single-word query, and to the longest token of a multi-word
    # one once the tokens are exhausted — a compound is a compound either way.
    head = max(tokens, key=len) if tokens else query
    for length in _prefix_lengths(len(head)):
        _add(head[:length])
        if len(out) >= MAX_CANDIDATES:
            break

    return out


def _prefix_lengths(full: int) -> list[int]:
    """Prefix lengths to try, longest first, ending at `MIN_TERM_LENGTH`.

    Spaced geometrically between the full word and the floor rather than by a
    fixed ratio, so the *last* attempt is always the maximally widened one no
    matter how long the input was. A fixed 30%-per-step schedule looked
    reasonable and was measured to be wrong: from "Betonsanierungsarbeiten" it
    reached 16, 11 and 7 characters and stopped, while the term that actually
    returns results is "Beton" at five. The last resort has to be an actual last
    resort.
    """
    if full <= MIN_TERM_LENGTH:
        return []
    ratio = (MIN_TERM_LENGTH / full) ** (1 / MAX_CANDIDATES)
    lengths: list[int] = []
    length = full
    for _ in range(MAX_CANDIDATES):
        length = max(MIN_TERM_LENGTH, int(length * ratio))
        if length < full and length not in lengths:
            lengths.append(length)
    return lengths


def widening_note(original: str, used: str, count: int) -> str:
    """The sentence that keeps a widened result from being read as an exact one.

    Names both terms on purpose. A model that sees only the results cannot tell
    that the question was changed under it, and a note saying merely "fuzzy
    match" does not let it warn the user which term actually produced the hits.
    """
    return (
        f"No exact match for {original!r}. These {count} result(s) are for the "
        f"broader term {used!r} — check that they answer the original question "
        f"before relying on them."
    )


def empty_note(original: str, tried: list[str], hint: str) -> str:
    """ARCH-003 criterion 3: an empty result must be actionable.

    Says what was tried, so the caller does not repeat a search that already
    failed, and points at the next useful move rather than stopping at "none".
    """
    attempts = ", ".join(repr(t) for t in [original, *tried])
    return (
        f"No match for {attempts}. {hint} "
        "If results are unexpectedly absent across several terms, call "
        "`source_status` — an upstream problem looks the same as an empty result "
        "from here."
    )
