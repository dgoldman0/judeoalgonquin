# N1 Pilot Source Packet

**Status:** Bounded manual research packet for candidate construction. It is not a frequency list, a bulk source import, or canon.

**Access date:** 2026-07-12

## Purpose and limits

The first architecture probe uses a deliberately small set of ordinary concepts and grammatical material. It tests whether the record model can keep source facts, conlang transformations, dependency revisions, literal translation, and idiomatic translation separate.

The Munsee material comes from John O'Meara's speaker-based dissertation on the Moraviantown variety. O'Meara says most fieldwork was conducted with Emily Johnson, Ethel Peters, and Beulah Timothy, while lesser amounts of information came from Mattie Huff, Enoch Jacobs, Peter Noah, Nellie Noah, and Rebecca Snake; he identifies all eight as Delaware speakers. This attribution applies to the dissertation as a whole: the selected examples are not attributed to individual speakers. The dissertation is copyrighted and publicly available for consultation through Library and Archives Canada. This project cites only a small number of forms and examples. It does not copy the dictionary or dissertation in bulk.

The Hebrew material is manually checked against the Academy of the Hebrew Language and, for historical lexical continuity, Brown–Driver–Briggs as hosted by Sefaria. Academy pages remain all-rights-reserved or of mixed/unclear reuse status; BDB's original text is public domain while the digital edition's license is version-specific. Neither source is bulk-ingested.

## Selected Hebrew evidence

| Candidate | Source fact | Locator | Pilot question |
|---|---|---|---|
| `בַּיִת` *bayit* | house/home, with other senses kept separate | Academy headword [`בַּיִת`](https://old.hebrew-academy.org.il/keyword/%D7%91%D6%BC%D6%B7%D7%99%D6%B4%D7%AA/); BDB displayed headword [`בַּ֫יִת`](https://www.sefaria.org/BDB%2C_%D7%91%D6%B7%D6%BC%D6%AB%D7%99%D6%B4%D7%AA) | Can a Hebrew ordinary-life stem enter a new class-sensitive plural rule? |
| `מַיִם` *mayim* | water; source number behavior is not automatically imported | Academy [terminology result](https://terms.hebrew-academy.org.il/munnah/1535_2/water); BDB displayed headword [`מַי 1`](https://www.sefaria.org/BDB%2C_%D7%9E%D6%B7%D7%99.1?lang=bi&with=all), whose entry treats `מַיִם` | Can mass-noun behavior remain explicit rather than being inferred from English? |
| `לֶחֶם` *leḥem* | bread; the broader historical “food” sense is a separate sense question | Academy headword [`לֶחֶם`](https://old.hebrew-academy.org.il/keyword/%D7%9C%D6%B6%D7%97%D6%B6%D7%9D/); BDB displayed headword [`לֶ֫חֶם 1`](https://www.sefaria.org/BDB%2C_%D7%9C%D6%B6%D6%AB%D7%97%D6%B6%D7%9D.1) | Can the database avoid silently merging bread with food? |
| `וְ־` historical *wə-*, modern ordinarily *ve-* with allomorphy | ordinary coordinator “and,” distinct from narrative waw | Academy [vocalization ruling](https://hebrew-academy.org.il/meeting/%D7%A8%D7%A0%D7%97/); [ordinary conjunction versus narrative waw](https://hebrew-academy.org.il/%D7%95-%D7%94%D7%94%D7%99%D7%A4%D7%95%D7%9A/) | May the contact language regularize one coordinator form without claiming that regularization is Hebrew? |
| `הַ־` *ha-* | definite article with conditioned Hebrew vocalization | Academy [definiteness overview](https://hebrew-academy.org.il/category/%D7%99%D7%99%D7%93%D7%95%D7%A2/); [vocalization rules](https://hebrew-academy.org.il/topic/hahlatot/grammardecisions/formation-and-vocalization/2-4-%D7%A2%D7%A0%D7%99%D7%99%D7%A0%D7%99-%D7%A0%D7%99%D7%A7%D7%95%D7%93-%D7%A9%D7%95%D7%A0%D7%99%D7%9D/) | Does an adapted article add useful definiteness, or later conflict with discourse-based marking? |

## Selected Munsee evidence

All locators below refer to O'Meara, *Delaware Stem Morphology* (1990), in the public [Library and Archives Canada PDF](https://www.collectionscanada.ca/obj/thesescanada/vol1/QMM/TC-QMM-39236.pdf).

| Candidate | Source fact | Thesis locator | Pilot question |
|---|---|---|---|
| `lənəw`, plural `lənəwak` | animate noun “man/men” | p. 5, §1.3.1, example 1.1a | Can an exactly attributed regional form participate in Hebrew-derived definiteness without being relabeled or culturally embellished? |
| `asən` | monomorphemic noun “stone”; class not stated at this locator | p. 37, example 1.32 | Can uncertainty remain explicit instead of guessing an animacy class? |
| `-ak` | animate-noun plural suffix | p. 5, §1.3.1, example 1.1a | Can the project test a class-sensitive plural without prematurely accepting the whole nominal paradigm? |
| `-al` | inanimate-noun plural suffix | p. 5, §1.3.1, example 1.1b | What happens when the adapted rule is applied to a Hebrew-derived stem? |
| inferred candidate `/pəmsii-/`; printed `/nə-pəmsii/` → `mpəmsi` | “I walk”; the first-person surface form demonstrates R32, but this locator neither prints the standalone stem nor states a verb-class label | p. 53, R32 example | Can the record model preserve attested analysis, explicit inference, surface form, and a deliberately unresolved class separately? |
| `/wələsii-/`; `wələsəw` | AI “he is good, pretty,” from root `/wəl-/` plus state final `/-əsii/` and third-person `-w` | p. 58, example 2.1a | Can a predicate remain a predicate rather than being flattened into an English-style free adjective? |

## Provisional script probe

Hebrew-derived candidates retain their cited Hebrew spelling. Munsee-derived
candidates use the reversible pointed analytic transport specified in
[O'Meara-to-Hebrew Analytic Transport](omeara-hebrew-transport.md). The source
transcription remains authoritative in `source_evidence`; the transport never
overwrites or silently repairs it.

This profile supersedes the pilot's incomplete teaching transcription. In
particular, it uses `k` → `ק`, consonantal `w` → `וו`, and sheva only for
source `ə`; a consonant with no source vowel is bare. Every affected pilot
record receives a new revision and machine-readable script provenance.

The analytic transport remains noncanonical. It supports exact storage, search,
and round-trip validation, but not community-preferred spelling, automatic
surface realization, or a claim about the language's final phonology.

## What this packet does not authorize

- no wholesale extraction from either source tradition;
- no claim that the selected items are the statistically most frequent words;
- no canonical Munsee-derived spelling;
- no complete plural, person, animacy, or definiteness system;
- no direct/inverse, obviation, or narrative-engine morphology; and
- no automated generation of additional language forms from these examples.
