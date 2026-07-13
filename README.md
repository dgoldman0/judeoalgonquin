# Judeo-Algonquin Language Knowledge Base

This repository is the structured knowledge base for an intentionally constructed language with two full cultural and linguistic parents: a continuing Judean/Hebrew civilization and the Algonquian peoples and languages encountered in the Hudson/Mahicanituck Valley.

Its explicit alternate-history premise imagines that Judea does not fall, that a culturally rich Judean community eventually crosses the Atlantic and settles in the valley, and that long contact produces a pidgin and then a nativized creole—a full community language that continues to elaborate across ordinary life, learning, art, narrative, and public institutions. Hebrew language and culture are preserved and transformed throughout that development. This is worldbuilding, not claimed history or reconstruction, and the project does not represent any real Jewish or Indigenous community's speech.

The project is currently in its **foundation / first N1 contact-lexicon
probe**. The knowledge base now contains 107 records: 72 source-facing donor
lexemes or morphemes, 15 actual contact-language lexeme proposals, and 20
construction, phrase, and sentence probes. Every record remains noncanonical. No legacy
translation is canonical. The old fine-tuning-era tree remains recoverable from
the archival Git tags documented in [the legacy audit](docs/legacy-audit.md).

## Start here

1. [Language goals](docs/language-goals.md) — highest project authority
2. [Language specification](docs/language-spec.md) — accepted and proposed language rules
3. [Hybrid narrative engine](docs/narrative-engine.md) — wayyiqtol, weqatal, and obviation
4. [Contact phonology and lexical formation](docs/contact-phonology-and-formation.md)
5. [Provenance and cultural policy](docs/provenance-and-cultural-policy.md)
6. [Data model and workflow](docs/data-model-and-workflow.md)
7. [Roadmap](docs/roadmap.md)
8. [Decision record](docs/decisions.md)
9. [Legacy audit](docs/legacy-audit.md)
10. [Initial-build budget](docs/initial-build-budget.md)
11. [Source registry](references/sources.yaml)
12. [Creative anchors](references/creative-anchors/README.md)
13. [N1 pilot source packet](docs/research/n1-pilot-source-packet.md)
14. [N1 core lexical epoch](docs/research/n1-core-epoch.md)
15. [O'Meara-to-Hebrew analytic transport](docs/research/omeara-hebrew-transport.md)
16. [N1 core embedding report](docs/reports/n1-core-embedding-evaluation-2026-07-12.json)
17. [N1 contact-synthesis report](docs/reports/n1-contact-synthesis-2026-07-12.json)

## Core rules

- Structured, revisioned records are the source of truth. Embeddings are disposable retrieval indexes.
- Source-facing donor records are evidence ingredients, not language words; contact-language proposals are separate revision-pinned records.
- Every source-language claim must name the exact language or lect and cite a source.
- Munsee Delaware is the regional Algonquian anchor. Broader Algonquian sources may fill documented gaps only with exact attribution and review.
- Modern/common Hebrew is living material for ordinary life; Biblical and Classical Hebrew are important narrative and literary resources. Hebrew may contribute vocabulary, morphology, and discourse in any domain.
- A defining expressive target combines an adapted Biblical Hebrew **wayyiqtol** event chain, an adapted **weqatal** consequence/habitual frame, and Algonquian-inspired proximate/obviative participant tracking. The combined behavior is required; its exact morphology must still be sourced and tested.
- Historical etymology and project formation rationale are separate fields.
- Automation may propose and check entries; only a human may make an entry canonical.
- Development advances by level: vocabulary, then phrases, then sentences, and eventually paragraphs.
- Paid embedding work is explicit, narrowly capped, recorded, and disabled again after each owner-authorized checkpoint.

No fine-tuning data, generated translation, or uncited vocabulary is imported as canon. The exact wording, themes, voice, and ambitions of *We Walk Well* and *When the Lights Learn Our Names* remain active revision input; their individual language forms are reviewable.

## Local setup and checks

Python 3.12 or newer is required. Runtime record checks and local search use the standard library; the development requirements add independent JSON Schema validation and the OpenAI SDK used only by explicitly live embedding commands.

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

Common local commands:

```bash
# Validate the intentionally noncanonical test fixtures.
PYTHONPATH=src .venv/bin/python -m judeoalgonquin validate \
  --data tests/fixtures/creative_anchor_candidates.jsonl

# Build an ignored local index, then use exact/normalized/full-text search.
PYTHONPATH=src .venv/bin/python -m judeoalgonquin build \
  --data tests/fixtures/creative_anchor_candidates.jsonl
PYTHONPATH=src .venv/bin/python -m judeoalgonquin search home

# Show the embedding plan without spending anything.
PYTHONPATH=src .venv/bin/python -m judeoalgonquin embed --data data/entries

# Validate all 107 records and declared constructions, then inspect the current
# dry-run embedding envelope without spending.
PYTHONPATH=src .venv/bin/python -m judeoalgonquin validate --data data/entries
PYTHONPATH=src .venv/bin/python -m judeoalgonquin evaluate --data data/entries
PYTHONPATH=src .venv/bin/python -m judeoalgonquin n1-core-embedding-eval
```

Paid embedding and semantic-search paths require both `--live` and an enabled,
capped authorization in [`config/api-budget.json`](config/api-budget.json). The
foundation smoke call, architecture-probe sanity call, and first N1 core
checkpoint have been consumed. The committed policy is disabled, so any further
paid action requires new owner approval.
