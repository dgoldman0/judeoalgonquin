"""Reversible Hebrew-script transport for cited O'Meara 1990 transcription.

This is an analytic display encoding for noncanonical research candidates. It is
not a phoneme inventory, a pronunciation engine, or a community orthography.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

from .normalize import nfc


MUNSEE_TRANSPORT_PROFILE = "omeara_hebrew_transport"
HEBREW_RETAINED_PROFILE = "hebrew_source_retained"
COMPONENTWISE_PROFILE = "componentwise_analytic"
PROJECT_SCHEMATIC_PROFILE = "project_schematic"
LEGACY_UNVERIFIED_PROFILE = "legacy_unverified"


CONSONANTS = {
    "p": "פּ",
    "t": "ט",
    "č": "צ׳",
    "k": "ק",
    "s": "ס",
    "š": "שׁ",
    "x": "כ",
    "h": "ה",
    "m": "מ",
    "n": "נ",
    "l": "ל",
    "w": "וו",
    "y": "יי",
}
VOWELS = ("aa", "ee", "ii", "oo", "a", "e", "i", "o", "ə")
_VOWEL_MARKS = {
    "a": "ַ",
    "aa": "ָ",
    "e": "ֶ",
    "ee": "ֵ",
    "i": "ִ",
    "ii": "ִ",
    "o": "ֹ",
    "ə": "ְ",
}
_FINAL_BASES = {"פ": "ף", "צ": "ץ", "כ": "ך", "מ": "ם", "נ": "ן"}
_MEDIAL_BASES = {value: key for key, value in _FINAL_BASES.items()}
_TOKEN_RE = re.compile(
    "|".join(
        re.escape(token)
        for token in sorted([*CONSONANTS, *VOWELS, "-", " "], key=len, reverse=True)
    )
)


@dataclass
class _Unit:
    kind: str
    source: str
    text: str
    has_vowel: bool = False


def normalize_munsee_input(value: str) -> str:
    """Normalize only representation-level details; never infer missing segments."""

    if not isinstance(value, str) or not value:
        raise ValueError("Munsee transport input must be a non-empty string")
    normalized = nfc(value.strip().lower())
    if normalized != value.strip():
        # Case folding is allowed, but decomposed or compatibility spellings are not
        # silently accepted as source-exact input.
        if nfc(value.strip()).lower() != normalized:
            raise ValueError("Munsee transport input must use declared NFC symbols")
    return normalized


def _tokens(value: str) -> list[str]:
    if "sh" in value or "ch" in value:
        raise ValueError(
            "unsupported practical spelling sequence; use declared source š or č"
        )
    tokens: list[str] = []
    position = 0
    while position < len(value):
        match = _TOKEN_RE.match(value, position)
        if match is None:
            raise ValueError(
                f"unsupported O'Meara transport symbol at character {position}: "
                f"{value[position]!r}"
            )
        tokens.append(match.group(0))
        position = match.end()
    return tokens


def _add_mark(text: str, mark: str) -> str:
    if text.endswith("׳"):
        return text[:-1] + mark + "׳"
    return text + mark


def _add_vowel(unit: _Unit, vowel: str) -> None:
    if vowel == "oo":
        unit.text += "וֹ"
    else:
        unit.text = _add_mark(unit.text, _VOWEL_MARKS[vowel])
        if vowel == "aa":
            unit.text += "א"
        elif vowel in {"ee", "ii"}:
            unit.text += "י"
    unit.has_vowel = True


def encode_munsee_transport(value: str) -> str:
    """Encode declared source-transcription tokens as reversible pointed Hebrew."""

    normalized = normalize_munsee_input(value)
    units: list[_Unit] = []
    for token in _tokens(normalized):
        if token in CONSONANTS:
            units.append(_Unit("consonant", token, CONSONANTS[token]))
        elif token in VOWELS:
            if units and units[-1].kind == "consonant" and not units[-1].has_vowel:
                _add_vowel(units[-1], token)
            else:
                carrier = _Unit("carrier", token, "א")
                _add_vowel(carrier, token)
                units.append(carrier)
        elif token == "-":
            units.append(_Unit("boundary", token, "־"))
        elif token == " ":
            units.append(_Unit("space", token, " "))

    for index, unit in enumerate(units):
        if unit.kind != "consonant" or unit.has_vowel or unit.source not in {"p", "č", "x", "m", "n"}:
            continue
        at_word_edge = index + 1 == len(units) or units[index + 1].kind == "space"
        if not at_word_edge:
            continue
        decomposed = unicodedata.normalize("NFD", unit.text)
        base = decomposed[0]
        if base in _FINAL_BASES:
            suffix = "׳" if unit.source == "č" else ""
            unit.text = _FINAL_BASES[base] + suffix
    return nfc("".join(unit.text for unit in units))


@dataclass(frozen=True)
class _Cluster:
    base: str
    marks: tuple[str, ...]


def _clusters(value: str) -> list[_Cluster | str]:
    result: list[_Cluster | str] = []
    for character in unicodedata.normalize("NFD", value):
        if character == "־" or character == " ":
            result.append(character)
        elif unicodedata.combining(character):
            if not result or not isinstance(result[-1], _Cluster):
                raise ValueError("Hebrew transport mark lacks a base letter")
            prior = result[-1]
            result[-1] = _Cluster(prior.base, (*prior.marks, character))
        elif character == "׳":
            result.append(character)
        else:
            result.append(_Cluster(character, ()))
    return result


def _mark_vowel(marks: tuple[str, ...]) -> str | None:
    vowel_marks = [mark for mark in marks if mark in set(_VOWEL_MARKS.values())]
    if len(vowel_marks) > 1:
        raise ValueError("Hebrew transport cluster contains multiple vowel marks")
    if not vowel_marks:
        return None
    return {
        "ַ": "a",
        "ָ": "aa",
        "ֶ": "e",
        "ֵ": "ee",
        "ִ": "i",
        "ֹ": "o",
        "ְ": "ə",
    }[vowel_marks[0]]


def _consume_consonant(clusters: list[_Cluster | str], index: int) -> tuple[str, tuple[str, ...], int]:
    item = clusters[index]
    if not isinstance(item, _Cluster):
        raise ValueError("expected a Hebrew transport consonant")
    base = _MEDIAL_BASES.get(item.base, item.base)
    marks = item.marks
    if base == "ו" and not marks:
        if index + 1 < len(clusters) and isinstance(clusters[index + 1], _Cluster):
            second = clusters[index + 1]
            if second.base == "ו":
                return "w", second.marks, index + 2
    if base == "י" and not marks:
        if index + 1 < len(clusters) and isinstance(clusters[index + 1], _Cluster):
            second = clusters[index + 1]
            if second.base == "י":
                return "y", second.marks, index + 2
    if base == "צ" and index + 1 < len(clusters) and clusters[index + 1] == "׳":
        return "č", marks, index + 2
    reverse = {
        "פ": "p",
        "ט": "t",
        "ק": "k",
        "ס": "s",
        "כ": "x",
        "ה": "h",
        "מ": "m",
        "נ": "n",
        "ל": "l",
    }
    if base == "ש" and "ׁ" in marks:
        return "š", tuple(mark for mark in marks if mark != "ׁ"), index + 1
    if base == "פ" and "ּ" not in marks and item.base != "ף":
        raise ValueError("plain pe is not the declared transport for source p")
    if base == "פ":
        marks = tuple(mark for mark in marks if mark != "ּ")
    if base not in reverse:
        raise ValueError(f"unsupported Hebrew transport letter {item.base!r}")
    return reverse[base], marks, index + 1


def _decode_vowel_options(
    clusters: list[_Cluster | str], index: int, marks: tuple[str, ...]
) -> tuple[tuple[str, int], ...]:
    vowel = _mark_vowel(marks)
    if vowel is None:
        if index < len(clusters) and isinstance(clusters[index], _Cluster):
            next_item = clusters[index]
            if next_item.base == "ו" and "ֹ" in next_item.marks:
                return (("oo", index + 1),)
        return (("", index),)
    if "ָ" in marks:
        if index >= len(clusters) or not isinstance(clusters[index], _Cluster) or clusters[index].base != "א" or clusters[index].marks:
            raise ValueError("long aa transport must end in bare aleph")
        return (("aa", index + 1),)
    if "ֵ" in marks:
        if index >= len(clusters) or not isinstance(clusters[index], _Cluster) or clusters[index].base != "י" or clusters[index].marks:
            raise ValueError("long ee transport must end in bare yod")
        return (("ee", index + 1),)
    if "ִ" in marks:
        # Hiriq is the only ambiguous mark: a following bare yod can be the ii
        # mater or the first half of consonantal y (encoded as two yods).  Let
        # the recursive decoder try both analyses and retain only a candidate
        # that re-encodes to the exact input.
        options: list[tuple[str, int]] = [("i", index)]
        if (
            index < len(clusters)
            and isinstance(clusters[index], _Cluster)
            and clusters[index].base == "י"
            and not clusters[index].marks
        ):
            options.append(("ii", index + 1))
        return tuple(options)
    return ((vowel, index),)


def decode_munsee_transport(value: str) -> str:
    """Decode canonical output produced by the pointed transport profile.

    Hiriq plus yod is locally ambiguous with hiriq before consonantal ``y``.
    Decoding therefore explores both analyses and accepts exactly one source
    string whose canonical re-encoding matches the input.
    """

    if not isinstance(value, str) or not value or value != nfc(value):
        raise ValueError("Hebrew transport input must be a non-empty NFC string")
    clusters = _clusters(value)
    @lru_cache(maxsize=None)
    def parse(index: int) -> tuple[str, ...]:
        if index == len(clusters):
            return ("",)
        item = clusters[index]
        if item == "־":
            return tuple("-" + tail for tail in parse(index + 1))
        if item == " ":
            return tuple(" " + tail for tail in parse(index + 1))
        if not isinstance(item, _Cluster):
            return ()
        results: set[str] = set()
        if item.base == "א":
            try:
                options = _decode_vowel_options(clusters, index + 1, item.marks)
            except ValueError:
                return ()
            for vowel, next_index in options:
                if not vowel:
                    continue
                results.update(vowel + tail for tail in parse(next_index))
            return tuple(results)
        try:
            consonant, marks, next_index = _consume_consonant(clusters, index)
            options = _decode_vowel_options(clusters, next_index, marks)
        except ValueError:
            return ()
        for vowel, after_vowel in options:
            results.update(
                consonant + vowel + tail for tail in parse(after_vowel)
            )
        return tuple(results)

    candidates = {
        candidate
        for candidate in parse(0)
        if encode_munsee_transport(candidate) == value
    }
    if not candidates:
        raise ValueError("Hebrew input is not canonical output of the transport profile")
    if len(candidates) > 1:
        raise ValueError("Hebrew transport input has more than one source decoding")
    return candidates.pop()


def assert_transport_round_trip(value: str) -> str:
    normalized = normalize_munsee_input(value)
    encoded = encode_munsee_transport(normalized)
    decoded = decode_munsee_transport(encoded)
    if decoded != normalized:
        raise ValueError(f"transport round trip failed: {normalized!r} -> {decoded!r}")
    return encoded
