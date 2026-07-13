# Creative anchors

These two songs predate the structured language knowledge base and remain active design material:

- `we-walk-well.md`
- `when-the-lights-learn-our-names.md`

Their English concepts, voice, imagery, intended registers, and narrative ambitions are continuity constraints for the language. Their existing Judeo-Algonquin forms and grammatical commentary are revision inputs, not automatically canonical evidence. Work may edit them extensively when source verification or a more coherent grammar requires it, but should not silently replace their identity or discard what they are trying to make the language capable of saying.

The Markdown files remain the frozen source texts. Their operational continuity
ledgers live in `data/creative-anchors/`, validate against
`schema/creative-anchor.schema.json`, and map every one of the 41 physical song
segments to protected functions, editable elements, gaps, tests, and
revision-pinned language-record links. The ledgers never turn a creative form
into source attestation.

Run both structural and cross-record validation with:

```bash
PYTHONPATH=src .venv/bin/python -m judeoalgonquin validate-anchors \
  --anchors data/creative-anchors --data data/entries
```

Every lexical, phrase, sentence, and paragraph epoch must consult the ledgers
before choosing its coverage and update them when a new candidate fills a gap,
exposes a conflict, or materially departs from a protected function.
