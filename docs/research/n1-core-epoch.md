# N1 Core Lexical Epoch

**Status:** Completed bounded candidate checkpoint. This is not canon, a bulk
source extraction, or a claim of complete N1 coverage.

## Outcome target

The round added 60 source-grounded lexical or function records and 12 regression
compositions to the existing 20-record architecture probe. The working
database contains exactly 92 records:

- 20 revised records from the architecture probe, including its five explicit
  construction records;
- 60 new lexical stems, independent words, or carefully bounded morphemes;
- 8 new short phrases; and
- 4 new simple sentences.

The source parent for each concept followed attested availability, ordinary
usability, collision pressure, and the language-design rationale. The selection
was not made from an automatic Hebrew/Munsee quota. Both co-parent continuities
occur across ordinary-life domains rather than being segregated into
“cultural” versus “natural” vocabulary.

## Delivered source slice

| Parent evidence | Lexemes | Morphemes | Bounded content |
|---|---:|---:|---|
| Hebrew | 24 | 1 | people and kin, home, food, body, physical quality, time, quantity, questions, and negation |
| Moraviantown Munsee | 33 | 2 | 22 nouns, 8 paired TA/TI perception stems, 3 basic intransitive stems, and 2 bound noun finals |
| **Total** | **57** | **3** | **60 individually cited candidates** |

Coverage is sense-based. A polysemous source headword does not satisfy several
functions unless each sense is independently supported and intentionally
admitted. Major gaps remain—especially needs, richer qualities and states,
speech, transfer, spatial constructions, and a broader function-word layer.

## Source and reuse boundary

Hebrew ordinary-life candidates may use manually verified Academy of the Hebrew Language entries. BDB may add historical evidence only when its exact displayed form and historical sense are separately recorded; it is not required for every modern entry.

Munsee candidates remain a limited, manually selected research sample from speaker-based published material. The project will not scrape or reconstruct O'Meara's copyrighted dictionary or dissertation as a corpus. The unresolved `munsee_current_community_lexical_guidance` gap continues to block canonical Munsee-derived orthography and a systematic lexical import. This round can create individually cited candidates; it cannot claim community acceptance, preferred modern spelling, or canonical status.

Broader Algonquian sources enter only after a documented regional gap. Their language and lect labels remain visible and they are never relabeled as Munsee.

## Script gate

Hebrew-derived words retain their cited Hebrew spelling. Regional-source forms use a deterministic pointed Hebrew **analytic transcription profile**, not a proposed community orthography. The profile must:

- preserve the source Roman transcription as authoritative data;
- encode every admitted source segment and vowel-length distinction reversibly;
- reject symbols outside its documented inventory instead of guessing;
- keep morphological segmentation separate from Hebrew punctuation;
- declare known ambiguities and source-level uncertainty; and
- carry a machine-readable profile label on every affected record.

The profile exists to make candidates inspectable and searchable in the project's defining script. It cannot support canon, unpointed running prose, automatic conversion of unattested forms, or claims about historical spelling development.

## Composition regression set

The 12 regression compositions are tests, not a shortcut into the full phrase or sentence epoch. Each must use revision-pinned lexical records and an already explicit construction. No new productive rule may be smuggled into an example.

The set covers at least:

- nominal coordination;
- definiteness;
- class-sensitive number where the host class is explicit;
- one-place predication with a supported participant cell;
- both same-parent and cross-parent combinations.

Space and time are represented in the lexical and retrieval coverage, but not
forced into a composed expression before the project has an explicit locative
or temporal construction.

## Gates and final source audit

1. All exact source forms, glosses, categories, locators, speaker-attribution limits, and reuse policies receive independent review.
2. Every project inference is separated from source evidence.
3. The analytic script profile round-trips every regional-source candidate.
4. Runtime and JSON Schema validation pass.
5. Exact English, Hebrew-script, and Roman aliases retrieve their intended record or an explicitly reported homonym set.
6. Composition checks pass positive and deliberate negative cases.
7. Revision changes invalidate every affected downstream vector.
8. The embedding payload is dry-run with exact input count, byte count, conservative token ceiling, and dollar ceiling.

The initial gate review cleared the frozen call. A stricter independent
source-to-record comparison immediately afterward found four corrections: a
lost `š` in the Munsee cloth item, separate sourcing for the pointed form of
Hebrew “tomorrow,” and two locator refinements. Those four lexical revisions
invalidate four woman-dependent compositions as well. The final records take
precedence over the call manifest; the fingerprint gate correctly marks eight
vectors stale rather than hiding the correction.

## Paid checkpoint result

After the initial local gates passed, the owner-authorized checkpoint sent 92 record
projections and 12 frozen queries in one embeddings request. The 104 inputs
used 50,922 input tokens at an estimated cost of **$0.00101844**. All 12 intended
records ranked first: recall@1 = 1.0, recall@3 = 1.0, and mean reciprocal rank =
1.0. These project-authored queries are a retrieval diagnostic, not an
independent linguistic benchmark.

The paid gate was disabled immediately afterward. No generative-model API call
was made. Full hashes, rankings, limitations, and token accounting are recorded
in [the checkpoint report](../reports/n1-core-embedding-evaluation-2026-07-12.json).
The call was not repeated after the final source corrections: 84 vectors remain
fresh and eight await a future explicitly authorized incremental checkpoint.

## Later contact-layer reinterpretation

This checkpoint is now explicitly the donor inventory for the first contact
synthesis pass, not a completed vocabulary. The later pass leaves these records
and citations intact, types all source-facing lexemes and morphemes as
`donor_candidate`, and creates separate revision-pinned language records. See
[Contact Phonology and Lexical Formation](../contact-phonology-and-formation.md)
and the [local synthesis report](../reports/n1-contact-synthesis-2026-07-12.json).

The “84 fresh / eight stale” count above is the historical state immediately
after this checkpoint's source corrections. The contact reinterpretation
changes donor fingerprints and adds new records, so it intentionally supersedes
that vector-freshness state without repeating the paid call.

Official endpoint reference: <https://developers.openai.com/api/reference/resources/embeddings/methods/create>
