# O'Meara-to-Hebrew Analytic Transport

**Status:** Provisional research transport. It is reversible only in its fully
pointed form and is not a canonical Judeo-Algonquin orthography, a pronunciation
engine, or a claim about community-preferred Munsee spelling.

## Purpose and evidence boundary

The profile `omeara_hebrew_transport` gives individually researched forms from
O'Meara's 1990 scholarly transcription an inspectable Hebrew-script rendering.
The cited Roman form remains authoritative. Each record stores the exact source
form, the normalized input used by the converter, and whether that input is a
surface, citation, or morphophonemic representation.

O'Meara marks long vowels by doubling, uses hyphens for morpheme boundaries,
and may print slash forms at different analytical levels. Those conventions do
not by themselves license automatic surface realization. An analytical `v` for
an unknown vowel that always syncopates has no mapping here; a separately cited
surface form is required. Practical spellings and symbols outside the declared
inventory fail closed.

## Consonants

| Source | Transport | Source | Transport |
|---|---|---|---|
| `p` | `פּ` | `t` | `ט` |
| `č` | `צ׳` | `k` | `ק` |
| `s` | `ס` | `š` | `שׁ` |
| `x` | `כ` | `h` | `ה` |
| `m` | `מ` | `n` | `נ` |
| `l` | `ל` | `w` | `וו` |
| `y` | `יי` | | |

Final `p`, `č`, `x`, `m`, and `n` use the appropriate final Hebrew letter only
at a true word edge. An internal morpheme boundary does not trigger a final
letter. Doubled vav and yod keep consonantal `w` and `y` distinct from vowel
length markers.

## Vowels and zero

A vowel mark attaches to the preceding consonant. A word-initial vowel or a
vowel after another vowel receives an aleph carrier.

| Source | After a consonant | Initially |
|---|---|---|
| `a` | `◌ַ` | `אַ` |
| `aa` | `◌ָא` | `אָא` |
| `e` | `◌ֶ` | `אֶ` |
| `ee` | `◌ֵי` | `אֵי` |
| `i` | `◌ִ` | `אִ` |
| `ii` | `◌ִי` | `אִי` |
| `o` | `◌ֹ` | `אֹ` |
| `oo` | `◌וֹ` | `אוֹ` |
| `ə` | `◌ְ` | `אְ` |

Sheva always encodes source `ə`. A consonant without a following source vowel
is left bare; sheva never doubles as a zero-vowel marker. The unpointed Hebrew
form is consequently lossy and cannot be decoded reliably or used to recover
the original vowel-bearing source form.

## Boundaries and storage

- The exact cited form is preserved in `orthography.source_exact`.
- `orthography.normalized_input` is NFC and uses declared O'Meara symbols.
- ASCII hyphen is the analytical boundary; Hebrew display renders it as maqaf.
- Spaces remain word boundaries.
- Slash notation is represented by `input_level`, not copied into the language
  form.
- Stored output is NFC and contains no bidirectional-control characters.
- Hebrew-derived forms bypass this converter and retain their cited spelling.
- Hybrid forms are assembled componentwise from revision-pinned records; the
  whole expression is never passed through one source profile.

## Regression examples

| Input | Fully pointed transport |
|---|---|
| `lənəw` | `לְנְוו` |
| `asən` | `אַסְן` |
| `pəmsii` | `פְּמסִי` |
| `wələsii` | `ווְלְסִי` |
| `ak` | `אַק` |
| `al` | `אַל` |
| `w` | `וו` |
| `wələsəw` | `ווְלְסְוו` |

Every admitted transport form must satisfy
`decode(encode(normalized_input)) == normalized_input`. Runtime validation also
requires the stored Hebrew form to equal the encoder output.

## Deliberately unresolved

This profile does not decide the eventual contact-language phoneme inventory,
sound adaptation, stress, canonical romanization, preferred community spelling,
permanent Hebrew letter choices, phonotactics, personal or dialect variation,
or the realization of abstract morphology. Those decisions require their own
evidence and review.
