"""Unicode normalization shared by validation and search."""

from __future__ import annotations

import re
import unicodedata


_SPACE_RE = re.compile(r"\s+")
_HEBREW_MARK_RANGES = (
    (0x0591, 0x05BD),
    (0x05BF, 0x05BF),
    (0x05C1, 0x05C2),
    (0x05C4, 0x05C5),
    (0x05C7, 0x05C7),
)
_UNSAFE_CODEPOINTS = {
    0x061C,
    0x200E,
    0x200F,
    0x202A,
    0x202B,
    0x202C,
    0x202D,
    0x202E,
    0x2066,
    0x2067,
    0x2068,
    0x2069,
    0xFFFD,
}
_PUNCTUATION_TRANSLATION = str.maketrans(
    {
        "’": "'",
        "‘": "'",
        "ʼ": "'",
        "׳": "'",
        "־": "-",
        "–": "-",
        "—": "-",
    }
)


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _is_hebrew_mark(codepoint: int) -> bool:
    return any(start <= codepoint <= end for start, end in _HEBREW_MARK_RANGES)


def strip_hebrew_marks(text: str) -> str:
    """Remove cantillation and niqqud while retaining Hebrew letters and punctuation."""

    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in decomposed if not _is_hebrew_mark(ord(ch)))
    return nfc(stripped)


def normalize_search(text: str) -> str:
    text = strip_hebrew_marks(text).translate(_PUNCTUATION_TRANSLATION).casefold()
    return _SPACE_RE.sub(" ", text).strip()


def unsafe_codepoints(text: str) -> list[str]:
    found: list[str] = []
    for ch in text:
        cp = ord(ch)
        if 0xD800 <= cp <= 0xDFFF or cp in _UNSAFE_CODEPOINTS:
            found.append(f"U+{cp:04X}")
    return found


def is_nfc(text: str) -> bool:
    return unicodedata.is_normalized("NFC", text)
