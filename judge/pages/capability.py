"""The capability page: one capability across every model, and where it is quiet.

The model page asks "what is known about this model". This asks the transpose,
and the transpose has a failure the original does not.

WHY THIS IS NOT THE MODEL PAGE ROTATED

On a model page, a capability nobody discussed is one empty row among twelve
and a reader sees the gap. Here, a model nobody discussed is INVISIBLE unless
the page enumerates the registry - and the models most likely to be missing
are the new and the obscure, which are exactly the cheap ones this product
exists to recommend.

So the page lists every model in the registry, not every model with a cell. A
comparison drawn only over models people happened to post about is a
popularity ranking wearing a capability's name, and it would be systematically
wrong in the direction of the incumbents.

RANKING IS REFUSED HERE

Cells carry counts and a status, never a score (rule 3). Two models with
published cells are not thereby ordered, and any ordering this page invented
would be a synthesised number with a page to live on. Models are grouped by
STATE and sorted by name inside each group, which is a presentation decision
rather than a claim.

CONDITIONS STAY SPLIT (FR-25). One model can be published under
`tools:1-5` and negative above it, and that is the finding rather than an
inconsistency to resolve.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from judge.config import capabilities


@dataclass(frozen=True)
class ModelStanding:
    """One model's position on one capability."""

    model_version_id: str
    display_name: str
    buckets: tuple[tuple[str, str], ...] = ()  # (condition_bucket, status)
    phrases: tuple[str, ...] = ()
    voices: int = 0

    @property
    def unreported(self) -> bool:
        return not self.buckets

    @property
    def publishes(self) -> bool:
        return any(status == "published" for _, status in self.buckets)

    @property
    def conditional(self) -> bool:
        """Published under some conditions and not others - FR-25's whole point.

        Not an inconsistency. "Fine under 5 tools, breaks above 10" is the most
        useful thing this board can say, and it only exists because buckets are
        never merged.
        """
        statuses = {status for _, status in self.buckets}
        return len(statuses) > 1


@dataclass(frozen=True)
class CapabilityPage:
    """One capability, over the whole registry."""

    key: str
    failure_mode: str
    models: tuple[ModelStanding, ...] = ()

    @property
    def silent(self) -> bool:
        return self.failure_mode == "silent"

    @property
    def reported(self) -> tuple[ModelStanding, ...]:
        return tuple(m for m in self.models if not m.unreported)

    @property
    def unreported(self) -> tuple[ModelStanding, ...]:
        """Listed, not omitted. The models most likely to be here are the new
        and the obscure - the cheap ones worth recommending."""
        return tuple(m for m in self.models if m.unreported)

    @property
    def conditional(self) -> tuple[ModelStanding, ...]:
        return tuple(m for m in self.reported if m.conditional)

    @property
    def summary(self) -> str:
        total = len(self.models)
        if not total:
            return "No models are loaded, so this page is not a comparison."
        reported = len(self.reported)
        body = f"{reported} of {total} models in the registry have any reports on this capability."
        if reported < total:
            body += (
                f" The other {total - reported} are listed unreported rather "
                f"than omitted: a comparison over only the models people post "
                f"about ranks popularity, not capability."
            )
        if self.silent:
            body += (
                " This capability fails silently, so an absence of complaints "
                "about any model here is not evidence that it works."
            )
        return body


class CapabilityPageReader:
    """Reads `cell` and `model_version`. Writes nothing."""

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    def build(self, capability_key: str) -> CapabilityPage:
        known = capabilities()
        if capability_key not in known:
            raise KeyError(
                f"{capability_key!r} is not in contract/capabilities.yaml. Refused "
                f"rather than rendered empty: an unknown key would produce a page "
                f"reading 'nobody has reported on this', which is indistinguishable "
                f"from a real capability nobody has discussed."
            )

        # LEFT JOIN from `model_version`, so a model with no cell survives the
        # query as a row. An inner join here is the whole defect: it would
        # silently produce a page about the models people post about.
        rows = self._conn.execute(
            """
            SELECT mv.id, mv.display_name, c.condition_bucket, c.status,
                   c.consensus_phrase, c.independent_voices
            FROM model_version mv
            LEFT JOIN cell c
              ON c.model_version_id = mv.id AND c.capability_key = %s
            ORDER BY mv.display_name, c.condition_bucket
            """,
            (capability_key,),
        ).fetchall()

        grouped: dict[str, dict[str, Any]] = {}
        for mv_id, name, bucket, status, phrase, voices in rows:
            entry = grouped.setdefault(
                mv_id,
                {"name": name, "buckets": [], "phrases": [], "voices": 0},
            )
            if bucket is None:
                continue  # the LEFT JOIN's null side: a model with no cell
            entry["buckets"].append((bucket, status))
            if phrase:
                entry["phrases"].append(phrase)
            entry["voices"] += voices or 0

        return CapabilityPage(
            key=capability_key,
            failure_mode=known[capability_key].failure_mode,
            models=tuple(
                ModelStanding(
                    model_version_id=mv_id,
                    display_name=data["name"],
                    buckets=tuple(data["buckets"]),
                    phrases=tuple(data["phrases"]),
                    voices=data["voices"],
                )
                for mv_id, data in sorted(grouped.items(), key=lambda kv: kv[1]["name"] or kv[0])
            ),
        )
