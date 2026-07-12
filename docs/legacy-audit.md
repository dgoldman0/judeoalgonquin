# Legacy Audit

## Scope and conclusion

The fine-tuning-era repository was reviewed before the active language knowledge base was established. The review covered current Markdown, text, CSV, generated datasets, training scaffolding, and their Git history.

The conclusion was to preserve the work in Git history while importing **no legacy language record as canon**. The old material remains useful as evidence of project intent, failed approaches, desired expressive capacities, and regression ideas. It is not a trustworthy seed corpus.

## Recovery points

- `archive/main-before-clean-2026-07-12` points to commit `a848822abfdbc0dd2d2aa409bd3df93aa0d36017`, the prior tracked `main` state.
- `archive/final-wip-2026-07-12` points to commit `98fe6457c9ed41510b8e94c9dc3468c6276f31ce`, which preserves the final fine-tuning-era working changes.

The active branch removes legacy files normally; it does not rewrite or destroy those commits.

## Legacy authority finding

`judeo-algonquin.md` was the highest-level legacy design document. `training/tmp/evaluation.md` called it the “unified” grammar, while `training/tmp/structure.md` said the CSVs contained the most detailed information. This split was never resolved.

All principal design documents and song evaluations first appeared together in commit `4510d2c` on 2026-01-23. The only later change to `judeo-algonquin.md` was a name edit. Vocabulary and generated training material then expanded without a corresponding revision of the grammar, so repetition across the corpus is not independent confirmation.

The high-level goals carried into the foundation were:

- an openly constructed, functional Hebrew–Algonquian hybrid;
- a culturally rich Judean/Hebrew continuity and a regional Algonquian continuity acting as co-parents;
- Hebrew script plus Hebrew-derived ordinary lexicon, morphology, discourse, narrative, and literary material;
- productive, source-specific Algonquian influence rather than decorative loans;
- everyday, careful, and literary registers;
- participant-tracking and narrative ambitions; and
- mutual respect, coherence, and cultural grounding.

Specific legacy forms and paradigms were not retained.

## Evidence of source mismatch

The legacy goal document said Eastern Algonquian material, particularly Munsee/Lenape and Mahican, should be primary. The actual reference and training material did not follow that rule:

- `words.md` contained 153 Central Algonquian/Ojibwe list entries and 29 Eastern entries.
- All 932 rows of `algonquin_vocab_900plus.csv` were labeled Central Algonquian.
- `training/tmp/vocabulary.csv` had 615 nonblank records: 316 labeled Hebrew, 269 only generic Algonquian, 15 Lenape, 4 Ojibwe, and 2 Munsee.
- None of those vocabulary records carried a usable citation locator.

The 932-row CSV also showed obvious OCR/table-extraction damage, including merged headwords and digits substituted for letters.

## Major internal contradictions

Examples included:

- singular and plural collapsed into the same supposed person-prefix forms;
- a relative-clause example whose subject and verb person did not agree;
- first-person translations that omitted the prefix claimed to be obligatory;
- conflicting `-al` and `-ak` plurals for the same inanimate noun;
- `-ink` and `-ənk` presented both as free variants and as an inconsistency to eliminate;
- animacy and participant tracking described as optional in one document and mandatory in another;
- one binary obviative marker claimed to uniquely identify multiple distinct obviatives;
- “inverse” defined through animacy rather than an explicit participant hierarchy; and
- Hebrew preposition plus locative morphology treated as optional emphasis in one place and mandatory in another.

These issues are why the current specification marks the desired systems as proposed until full, sourced paradigms exist.

## False etymology and cultural overreach

Legacy `etymology` fields often supplied poetic or ideological explanations rather than history. They claimed, for example, that objects were grammatically animate because they participated in hospitality, that stones were living grandfathers, or that particular abstractions could not come from any language but Hebrew.

Other generated material invented treaties, scholarship, religious rulings, and shared Indigenous/Jewish ritual claims as if factual. Sacred medicines and ceremonial terms from Central sources were treated as a general-purpose Algonquian vocabulary pool.

The current policy therefore separates sourced etymology, project formation, and design rationale and applies heightened review to cultural and ceremonial material.

## Data-quality findings

- The forward vocabulary CSV and reverse CSV had different record counts.
- Exact duplicate English keys and duplicate conlang forms lacked stable sense IDs.
- Two legacy text files were not Unicode NFC-normalized.
- A vocabulary plan was stale on arrival relative to the expanded file created with it.
- Advanced translations were generated from the same unstable rules they were then used to evaluate, creating circular evidence.
- Generic Q&A, assistant conversations, toxicity/noise material, and fine-tune result logs carried no language authority.

## Disposition

### Intent extracted into new foundation documents

- high-level hybrid goals from `judeo-algonquin.md`;
- desired lyrical and narrative capacities from the song and narrative prototypes;
- the idea of level-by-level vocabulary expansion; and
- the need for grammar notes, translation notes, source explanations, revision, and retrieval.

### Archival reference only

- `judeo-algonquin.md` and its evaluations;
- `words.md` and its source links;
- narrative and long-prose prototypes other than the two active song anchors;
- metalinguistic and vocabulary-planning notes; and
- original sample pairs.

### Removed from the active tree

- all fine-tuning JSONL and result logs;
- generated vocabulary, reverse vocabulary, phrases, sentences, and prose;
- OCR-damaged reference CSVs;
- generic Q&A, conversation, noise, and validation data;
- obsolete conversion and translation scripts; and
- obsolete file-structure documentation.

An archival item may return only as a newly researched candidate with exact sources, explicit formation history, current validation, and human review.

### Active creative anchors

[*We Walk Well* and *When the Lights Learn Our Names*](../references/creative-anchors/README.md) are preserved in the active reference tree. Their wording, themes, voices, imagery, intended registers, and narrative ambitions remain revision input and continuity constraints. Their individual Judeo-Algonquin forms and grammatical commentary remain reviewable rather than canonical.
