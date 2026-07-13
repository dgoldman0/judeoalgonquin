import unittest

from judeoalgonquin.orthography import (
    CONTACT_POINTED_PROFILE,
    assert_contact_round_trip,
    assert_transport_round_trip,
    decode_contact_pointed,
    decode_munsee_transport,
    encode_contact_pointed,
    encode_contact_unpointed,
    encode_munsee_transport,
)
from judeoalgonquin.normalize import strip_hebrew_marks


class OrthographyTransportTests(unittest.TestCase):
    def test_required_pilot_examples(self) -> None:
        expected = {
            "lənəw": "לְנְוו",
            "asən": "אַסְן",
            "pəmsii": "פְּמסִי",
            "wələsii": "ווְלְסִי",
            "ak": "אַק",
            "al": "אַל",
            "w": "וו",
            "wələsəw": "ווְלְסְוו",
        }
        for source, hebrew in expected.items():
            with self.subTest(source=source):
                self.assertEqual(encode_munsee_transport(source), hebrew)
                self.assertEqual(decode_munsee_transport(hebrew), source)

    def test_short_long_and_consonant_mater_contrasts(self) -> None:
        forms = [
            "pa",
            "paa",
            "pe",
            "pee",
            "pi",
            "pii",
            "po",
            "poo",
            "pə",
            "pow",
            "piy",
            "sə",
            "šə",
            "ta",
            "ča",
            "ka",
            "xa",
        ]
        encoded = [assert_transport_round_trip(form) for form in forms]
        self.assertEqual(len(encoded), len(set(encoded)))

    def test_source_caron_affricate_is_preserved_not_normalized(self) -> None:
        for form in (
            "čankameekw",
            "pak-ii-nčəw",
            "tiih-ii-nčəw",
            "-nčəw",
        ):
            with self.subTest(form=form):
                self.assertEqual(
                    decode_munsee_transport(assert_transport_round_trip(form)),
                    form,
                )
        with self.assertRaisesRegex(ValueError, "unsupported"):
            encode_munsee_transport("cankameekw")

    def test_initial_vowels_clusters_boundaries_and_final_letters(self) -> None:
        for form in (
            "asən",
            "aap",
            "eex",
            "mohkw",
            "pənt-aw-",
            "aanay siipəw",
            "iya",
            "iiya",
            "iyiya",
            "iiyiiya",
        ):
            with self.subTest(form=form):
                self.assertEqual(
                    decode_munsee_transport(assert_transport_round_trip(form)),
                    form,
                )

    def test_unknown_practical_or_analytic_symbols_fail_closed(self) -> None:
        for form in ("sham", "bad", "ca", "a/v", "pəməsiiʼ", "nə-pəmsii/"):
            with self.subTest(form=form):
                with self.assertRaisesRegex(ValueError, "unsupported"):
                    encode_munsee_transport(form)

    def test_unpointed_transport_never_recovers_the_vowel_bearing_source(self) -> None:
        for source in ("lənəw", "asən", "pəmsii", "wələsəw"):
            with self.subTest(source=source):
                unpointed = strip_hebrew_marks(encode_munsee_transport(source))
                try:
                    decoded = decode_munsee_transport(unpointed)
                except ValueError:
                    continue
                self.assertNotEqual(decoded, source)

    def test_retained_hebrew_is_not_decodable_by_transport_profile(self) -> None:
        for value in ("בַּיִת", "מים"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    decode_munsee_transport(value)


class ContactPointedCandidateTests(unittest.TestCase):
    def test_profile_name_and_complete_consonant_inventory(self) -> None:
        self.assertEqual(CONTACT_POINTED_PROFILE, "contact_pointed_candidate")
        forms = [
            "pa",
            "ba",
            "fa",
            "va",
            "ta",
            "da",
            "ka",
            "ga",
            "ca",
            "ča",
            "sa",
            "za",
            "ša",
            "xa",
            "ha",
            "ma",
            "na",
            "la",
            "ra",
            "wa",
            "ya",
        ]
        encoded = [assert_contact_round_trip(form) for form in forms]
        self.assertEqual(len(encoded), len(set(encoded)))

    def test_vowel_quality_length_and_reduced_vowel_round_trip(self) -> None:
        forms = [
            "pa",
            "paa",
            "pe",
            "pee",
            "pi",
            "pii",
            "po",
            "poo",
            "pu",
            "pə",
        ]
        encoded = [assert_contact_round_trip(form) for form in forms]
        self.assertEqual(len(encoded), len(set(encoded)))

    def test_contact_adaptation_examples_and_boundaries(self) -> None:
        for form in (
            "iša",
            "lexem",
            "katan",
            "šulxan",
            "em wə-av",
            "pəməsii-w",
            "iya",
            "iiya",
        ):
            with self.subTest(form=form):
                hebrew = encode_contact_pointed(form)
                self.assertEqual(decode_contact_pointed(hebrew), form)

    def test_c_and_caron_affricate_and_final_pairs_remain_distinct(self) -> None:
        pairs = [("c", "č"), ("p", "f"), ("b", "v")]
        for first, second in pairs:
            with self.subTest(pair=(first, second)):
                first_hebrew = assert_contact_round_trip(first)
                second_hebrew = assert_contact_round_trip(second)
                self.assertNotEqual(first_hebrew, second_hebrew)

    def test_unpointed_alias_is_deliberately_lossy(self) -> None:
        self.assertEqual(encode_contact_unpointed("pa"), encode_contact_unpointed("fa"))
        self.assertEqual(encode_contact_unpointed("ba"), encode_contact_unpointed("va"))
        self.assertNotEqual(encode_contact_unpointed("pa"), encode_contact_pointed("pa"))

    def test_donor_spellings_outside_contact_inventory_fail_closed(self) -> None:
        for form in ("sham", "chad", "qatan", "leḥem"):
            with self.subTest(form=form):
                with self.assertRaisesRegex(ValueError, "unsupported"):
                    encode_contact_pointed(form)


if __name__ == "__main__":
    unittest.main()
