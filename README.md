# Judeo-Algonquin Language Knowledge Base

This repository is the structured knowledge base for an intentionally constructed language with two full cultural and linguistic parents: a continuing Judean/Hebrew civilization and the Algonquian peoples and languages encountered in the Hudson/Mahicanituck Valley.

Its explicit alternate-history premise imagines that Judea does not fall, that a culturally rich Judean community eventually crosses the Atlantic and settles in the valley, and that long contact produces a pidgin and then a nativized creole—a full community language that continues to elaborate across ordinary life, learning, art, narrative, and public institutions. Hebrew language and culture are preserved and transformed throughout that development. This is worldbuilding, not claimed history or reconstruction, and the project does not represent any real Jewish or Indigenous community's speech.

The project is currently in its **foundation / first architecture-probe** stage. Twenty N1 records now exercise the schema and retrieval workflow, but every one remains a noncanonical candidate. No legacy translation is canonical. The old fine-tuning-era tree remains recoverable from the archival Git tags documented in [the legacy audit](docs/legacy-audit.md).

## Start here

1. [Language goals](docs/language-goals.md) — highest project authority
2. [Language specification](docs/language-spec.md) — accepted and proposed language rules
3. [Hybrid narrative engine](docs/narrative-engine.md) — wayyiqtol, weqatal, and obviation
4. [Provenance and cultural policy](docs/provenance-and-cultural-policy.md)
5. [Data model and workflow](docs/data-model-and-workflow.md)
6. [Roadmap](docs/roadmap.md)
7. [Decision record](docs/decisions.md)
8. [Legacy audit](docs/legacy-audit.md)
9. [Initial-build budget](docs/initial-build-budget.md)
10. [Source registry](references/sources.yaml)
11. [Creative anchors](references/creative-anchors/README.md)
12. [N1 pilot source packet](docs/research/n1-pilot-source-packet.md)
13. [N1 embedding sanity report](docs/reports/n1-pilot-embedding-evaluation-2026-07-12.json)

## Core rules

- Structured, revisioned records are the source of truth. Embeddings are disposable retrieval indexes.
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

# Validate the N1 pilot's declared constructions, then inspect its fixed
# 20-record + 5-query single-request embedding evaluation without spending.
PYTHONPATH=src .venv/bin/python -m judeoalgonquin evaluate
PYTHONPATH=src .venv/bin/python -m judeoalgonquin pilot-embedding-eval
```

Paid embedding and semantic-search paths require both `--live` and an enabled, capped authorization in [`config/api-budget.json`](config/api-budget.json). The foundation smoke call and first N1 retrieval sanity call have been consumed. The committed policy is disabled, so any further paid action requires new owner approval.
