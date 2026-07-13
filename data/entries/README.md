# Reviewable language-record source

This directory contains structured language records that are the reviewable
source of truth and must validate against `schema/entry.schema.json`.
`n1-pilot.jsonl` contains the revised 20-record architecture probe;
`n1-core-lexicon.jsonl` adds 60 independently sourced lexical/function donor
candidates; `n1-core-regressions.jsonl` adds 12 revision-pinned composition
tests; `n1-contact-lexicon.jsonl` adds the first 15 actual contact-language
lexeme proposals; `n1-song-chorus.jsonl` adds 17 manually authored donor,
contact, construction, and sentence records for the first *We Walk Well*
chorus tranche; and `n1-perception-enrichment.jsonl` adds 20 manually authored
records for sound, class-sensitive perception, an objectful first-plural
Absolute, ordinary finite coordination, one phrase, and eight sentences.

The static-place tranche is split by review function:

- `n1-static-place-enrichment.jsonl` preserves six source-facing locative,
  predicate, and person-pattern records;
- `n1-static-place-contact.jsonl` adds eleven contact-language atoms, including
  the separate contact coordinator, mixed-host locative, `efo`, household
  nouns, and three AI stems;
- `n1-static-place-grammar.jsonl` adds five contact constructions; and
- `n1-static-place-examples.jsonl` adds six phrases and eight sentences.

Those four files contribute 36 records: 3 morphemes, 12 lexemes, 7
constructions, 6 phrases, and 8 sentences.

The ordinary motion-and-action tranche is likewise split by review function:

- `n1-motion-action-source.jsonl` preserves seven individually reviewed
  regional and Hebrew source records;
- `n1-motion-action-contact.jsonl` adds ten bounded contact lexemes for spatial
  relations, motion, drinking, finding, and door;
- `n1-motion-action-grammar.jsonl` adds five closed ordinary constructions; and
- `n1-motion-action-examples.jsonl` adds three spatial phrases and twenty
  ordinary sentences.

Those four files contribute 45 records: 17 lexemes, 5 constructions, 3
phrases, and 20 sentences. Their creative-anchor links record bounded influence
and partial coverage, not canon or source attestation. In particular, ordinary
motion, route, return, and find clauses supply no wayyiqtol foreground chain,
weqatal consequence frame, obviation, or narrative participant tracking.

The full 225-record database is explicitly noncanonical and remains subject to
source and design revision.

Every source-facing lexeme or morpheme is typed `donor_candidate`. It preserves
evidence but cannot itself become language canon. The contact records depend on
exact donor revisions and are typed `direct_contact_inheritance` or
`contact_native_formation`.

Legacy forms and generated examples belong in fixtures or creative references until they have been individually researched and reviewed. A SQLite database or embedding vector is always derived output and must not be committed here. Only an authorized human lifecycle review can promote a record toward canon.
