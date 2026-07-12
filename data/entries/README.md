# Reviewable language-record source

This directory contains structured language records that are the reviewable source of truth and must validate against `schema/entry.schema.json`. The current `n1-pilot.jsonl` is a bounded architecture probe: all 20 records are candidates, explicitly noncanonical, and subject to source and design revision.

Legacy forms and generated examples belong in fixtures or creative references until they have been individually researched and reviewed. A SQLite database or embedding vector is always derived output and must not be committed here. Only an authorized human lifecycle review can promote a record toward canon.
