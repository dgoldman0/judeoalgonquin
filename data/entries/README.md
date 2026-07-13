# Reviewable language-record source

This directory contains structured language records that are the reviewable
source of truth and must validate against `schema/entry.schema.json`.
`n1-pilot.jsonl` contains the revised 20-record architecture probe;
`n1-core-lexicon.jsonl` adds 60 independently sourced lexical/function
candidates; and `n1-core-regressions.jsonl` adds 12 revision-pinned composition
tests. All 92 records are explicitly noncanonical candidates and remain subject
to source and design revision.

Legacy forms and generated examples belong in fixtures or creative references until they have been individually researched and reviewed. A SQLite database or embedding vector is always derived output and must not be committed here. Only an authorized human lifecycle review can promote a record toward canon.
