import unittest

from judeoalgonquin.normalize import (
    is_nfc,
    nfc,
    normalize_search,
    strip_hebrew_marks,
    unsafe_codepoints,
)


class NormalizeTests(unittest.TestCase):
    def test_pointed_and_unpointed_hebrew_share_search_key(self) -> None:
        pointed = "וִיגְוָאם"
        self.assertEqual(normalize_search(pointed), normalize_search(strip_hebrew_marks(pointed)))

    def test_punctuation_and_space_normalization(self) -> None:
        self.assertEqual(normalize_search("  Path—Road  "), "path-road")
        self.assertEqual(normalize_search("yo׳wa"), "yo'wa")

    def test_nfc(self) -> None:
        decomposed = "e\u0301"
        self.assertFalse(is_nfc(decomposed))
        self.assertTrue(is_nfc(nfc(decomposed)))

    def test_unsafe_directional_control(self) -> None:
        self.assertEqual(unsafe_codepoints("safe\u202etext"), ["U+202E"])


if __name__ == "__main__":
    unittest.main()
