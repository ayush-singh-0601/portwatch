"""
Sanctions name matching using rapidfuzz.

Provides Unicode-aware name normalisation and high-performance fuzzy
matching suitable for screening vessel names, beneficial owners, and
corporate entities against consolidated sanctions lists.

Usage::

    from app.services.name_matcher import match_entity, batch_match

    results = match_entity("SEPAHAN OIL CO", sanctions_names, threshold=85.0)
    batch  = batch_match(entity_names, sanctions_names, threshold=85.0)
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import re
import unicodedata

from rapidfuzz import fuzz, process


@dataclass
class MatchResult:
    """Result of a fuzzy name match against a sanctions list entry.

    Attributes:
        matched_name: The sanctions list entry name that matched.
        score: Confidence score (0-100).
        match_type: Classification of the match — ``exact``, ``fuzzy``,
            or ``alias``.
    """

    matched_name: str
    score: float
    match_type: str


@lru_cache(maxsize=16384)
def normalize_name(name: str) -> str:
    """Normalize a name for comparison.

    Steps:
    1. NFKD Unicode normalization (decompose ligatures, etc.).
    2. Strip accents / combining marks.
    3. Lowercase.
    4. Remove punctuation (keep letters, digits, whitespace).
    5. Collapse multiple spaces.

    Args:
        name: Raw name string.

    Returns:
        Normalized name ready for fuzzy comparison.

    Examples:
        >>> normalize_name("SOCIÉTÉ MARITIME D'INVESTISSEMENT")
        'societe maritime dinvestissement'
        >>> normalize_name("Al-Quds Corp.")
        'alquds corp'
    """
    if not name:
        return ""

    # NFKD decomposition
    text = unicodedata.normalize("NFKD", name)

    # Strip combining characters (accents, diacritics)
    text = "".join(c for c in text if not unicodedata.combining(c))

    # Lowercase
    text = text.lower()

    # Remove everything that isn't a letter, digit, or whitespace
    text = re.sub(r"[^\w\s]", "", text)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


_NORMALIZED_SANCTIONS_CACHE: dict[int, tuple[int, list[str]]] = {}


def _get_normalized_sanctions(sanctions_list: list[str]) -> list[str]:
    """Retrieve or compute and cache normalized strings for a sanctions list."""
    cache_key = id(sanctions_list)
    list_len = len(sanctions_list)
    cached = _NORMALIZED_SANCTIONS_CACHE.get(cache_key)
    if cached is not None and cached[0] == list_len:
        return cached[1]

    normalized = [normalize_name(s) for s in sanctions_list]
    _NORMALIZED_SANCTIONS_CACHE[cache_key] = (list_len, normalized)
    return normalized


def pre_normalize_sanctions(sanctions_list: list[str]) -> list[str]:
    """Pre-normalize and cache sanctions entity names for repeated screening calls."""
    return _get_normalized_sanctions(sanctions_list)


def match_entity(
    name: str,
    sanctions_list: list[str],
    threshold: float = 85.0,
    normalized_sanctions: list[str] | None = None,
) -> list[MatchResult]:
    """Match a single entity name against a sanctions list using fuzzy matching.

    Uses ``rapidfuzz.fuzz.WRatio`` which combines multiple strategies
    (ratio, partial, token-sort, token-set) for the most robust score.

    Args:
        name: Entity name to screen.
        sanctions_list: List of sanctions entry names.
        threshold: Minimum score (0-100) to include in results.
        normalized_sanctions: Optional pre-normalized list of sanctions names.

    Returns:
        List of ``MatchResult`` objects sorted by descending score.
    """
    if not name or not sanctions_list:
        return []

    normalized_input = normalize_name(name)
    if normalized_sanctions is None:
        normalized_sanctions = _get_normalized_sanctions(sanctions_list)

    matches = process.extract(
        query=normalized_input,
        choices=normalized_sanctions,
        scorer=fuzz.WRatio,
        score_cutoff=threshold,
        limit=10,
    )

    results: list[MatchResult] = []
    for matched_norm, score, idx in matches:
        original_name = sanctions_list[idx] if 0 <= idx < len(sanctions_list) else matched_norm

        # Classify match type
        if score >= 99.5:
            match_type = "exact"
        else:
            match_type = "fuzzy"

        results.append(
            MatchResult(
                matched_name=original_name,
                score=round(score, 2),
                match_type=match_type,
            )
        )

    # Sort by descending score
    results.sort(key=lambda r: r.score, reverse=True)

    return results


def batch_match(
    entities: list[str],
    sanctions: list[str],
    threshold: float = 85.0,
    normalized_sanctions: list[str] | None = None,
) -> dict[str, list[MatchResult]]:
    """Batch-match multiple entity names against a sanctions list.

    Uses ``rapidfuzz.process.cdist`` internally for performance when
    both lists are large (O(n*m) comparisons).

    Args:
        entities: List of entity names to screen.
        sanctions: List of sanctions entry names.
        threshold: Minimum score to include.
        normalized_sanctions: Optional pre-normalized list of sanctions names.

    Returns:
        Dictionary mapping each input entity name to its list of
        ``MatchResult`` objects.
    """
    if not entities or not sanctions:
        return {}

    normalized_entities = [normalize_name(e) for e in entities]
    if normalized_sanctions is None:
        normalized_sanctions = _get_normalized_sanctions(sanctions)

    results: dict[str, list[MatchResult]] = {}

    try:
        score_matrix = process.cdist(
            queries=normalized_entities,
            choices=normalized_sanctions,
            scorer=fuzz.WRatio,
            workers=-1,
        )

        for i, entity_name in enumerate(entities):
            entity_matches: list[MatchResult] = []
            for j, sanctions_name in enumerate(sanctions):
                score = float(score_matrix[i][j])
                if score >= threshold:
                    match_type = "exact" if score >= 99.5 else "fuzzy"
                    entity_matches.append(
                        MatchResult(
                            matched_name=sanctions_name,
                            score=round(score, 2),
                            match_type=match_type,
                        )
                    )

            entity_matches.sort(key=lambda r: r.score, reverse=True)
            results[entity_name] = entity_matches

    except (ImportError, ModuleNotFoundError, Exception):
        for entity_name in entities:
            results[entity_name] = match_entity(
                entity_name,
                sanctions,
                threshold=threshold,
                normalized_sanctions=normalized_sanctions,
            )

    return results


class NameMatcher:
    """Object-oriented wrapper around the fuzzy matching functions.

    Usage::

        matcher = NameMatcher(threshold=85.0)
        results = matcher.match_entity("SEPAHAN OIL CO", sanctions_names)
    """

    def __init__(self, threshold: float = 85.0, sanctions_list: list[str] | None = None):
        self.threshold = threshold
        self._sanctions_cache: dict[int, list[str]] = {}
        if sanctions_list is not None:
            self.set_sanctions(sanctions_list)

    def set_sanctions(self, sanctions_list: list[str]) -> list[str]:
        """Pre-normalize and cache a sanctions list for screening."""
        normalized = _get_normalized_sanctions(sanctions_list)
        self._sanctions_cache[id(sanctions_list)] = normalized
        return normalized

    def match_entity(
        self,
        name: str,
        sanctions_list: list[str],
        normalized_sanctions: list[str] | None = None,
    ) -> list[MatchResult]:
        """Fuzzy-match a single name against the sanctions list."""
        if normalized_sanctions is None:
            normalized_sanctions = self._sanctions_cache.get(id(sanctions_list))
        return match_entity(
            name,
            sanctions_list,
            threshold=self.threshold,
            normalized_sanctions=normalized_sanctions,
        )

    def batch_match(
        self,
        entities: list[str],
        sanctions: list[str],
        normalized_sanctions: list[str] | None = None,
    ) -> dict[str, list[MatchResult]]:
        """Batch fuzzy-match multiple entities."""
        if normalized_sanctions is None:
            normalized_sanctions = self._sanctions_cache.get(id(sanctions))
        return batch_match(
            entities,
            sanctions,
            threshold=self.threshold,
            normalized_sanctions=normalized_sanctions,
        )

    @staticmethod
    def exact_match(name: str, sanctions_list: list[str]) -> list[str]:
        """Find exact normalized matches for a name in the sanctions list."""
        normalized_input = normalize_name(name)
        normalized_sanctions = _get_normalized_sanctions(sanctions_list)
        matches = []
        for orig, norm in zip(sanctions_list, normalized_sanctions):
            if norm == normalized_input:
                matches.append(orig)
        return matches

