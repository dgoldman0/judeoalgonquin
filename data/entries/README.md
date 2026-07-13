# Reviewable language-record source

This directory contains structured language records that are the reviewable
source of truth and must validate against `schema/entry.schema.json`.
`n1-pilot.jsonl` contains the revised 20-record architecture probe;
`n1-core-lexicon.jsonl` adds 60 independently sourced lexical/function donor
candidates; `n1-core-regressions.jsonl` adds 12 revision-pinned composition
tests; and `n1-contact-lexicon.jsonl` adds the first 15 actual contact-language
lexeme proposals. The full 107-record database is explicitly noncanonical and
remains subject to source and design revision.

Every source-facing lexeme or morpheme is typed `donor_candidate`. It preserves
evidence but cannot itself become language canon. The contact records depend on
exact donor revisions and are typed `direct_contact_inheritance` or
`contact_native_formation`.

Legacy forms and generated examples belong in fixtures or creative references until they have been individually researched and reviewed. A SQLite database or embedding vector is always derived output and must not be committed here. Only an authorized human lifecycle review can promote a record toward canon.
