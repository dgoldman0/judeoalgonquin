# Roadmap

The roadmap builds a translation knowledge base through repeated, gated epochs. It is not a one-pass content-generation schedule.

## Phase 0 — Foundation and safety

Deliverables:

- authority, language-goal, specification, provenance, workflow, and decision documents;
- a verified source registry with reuse status;
- structured schemas and local validation;
- exact search and dependency tracking;
- deterministic fixtures that confer no inherited canonical status;
- preserved, linked creative-anchor sources for *We Walk Well* and *When the Lights Learn Our Names*;
- embedding adapter and explicit model, dimensions, and content-fingerprint metadata; and
- one small live embedding smoke test.

Gate:

- all local tests pass;
- unresolved language choices are explicitly marked;
- no inherited language record has become canonical without current review;
- the [creative anchors](../references/creative-anchors/README.md) are preserved as revision input without treating their individual forms as proof;
- no paid work beyond the one smoke test has occurred; and
- the project owner receives the test and spending report.

## Project proficiency levels

These are project levels, not CEFR equivalences.

### N1 — Novice core

Immediate reference, basic participants, common actions and states, essential questions, simple quantities, time, place, and ordinary needs. Sentences use only the first accepted constructions.

Coverage includes ordinary Judean/Hebrew cultural continuity rather than postponing the Hebrew parent to literary levels.

### N2 — Novice extended

Routine description, possession, comparison, negation, requests, basic coordination, common spatial and temporal relations, and a broader daily-life lexicon.

### D1 — Developing connected language

Multi-clause coordination, reasons and consequences, basic subordination, and productive derivation. D1 must prototype and separately test a wayyiqtol-derived foreground chain, a weqatal-derived consequence/habitual frame, and controlled proximate/obviative participant tracking.

### D2 — Developing complex language

Rich subordinate and compound sentences, register choice, abstraction without source-language stereotyping, reported speech, discourse shifts, and sustained consistency across several sentences. D2 must combine the three narrative mechanisms in short multi-participant scenes and demonstrate a recoverable discourse-center shift plus an event-to-enduring-pattern transition.

### R1 — Rich language

Paragraphs, edited prose, literary narrative, argument, explanation, and stylistic variation with fully traceable dependencies and revisions.

At this level the language must be able to revisit both creative anchors without erasing their distinct voices: communal lyric and interdependence in *We Walk Well*, and fast modern narrative, humor, and the full wayyiqtol–weqatal–obviation synthesis in *When the Lights Learn Our Names*.

Level membership is coverage- and competency-based. Word-count targets may be added after the first measured epochs; arbitrary counts do not define mastery.

## The epoch cycle

Every level follows the same order.

### 1. Vocabulary epoch

- define the level's semantic and grammatical coverage;
- research exact source forms and source-language categories;
- propose lexemes and morphemes;
- retrieve neighbors before coining or adapting;
- check collisions, gaps, provenance, and formation logic; and
- obtain human canon decisions.

### 2. Phrase epoch

- combine canonical vocabulary through accepted constructions;
- cover frequent collocations and non-sentential functions;
- test inflection, ordering, phonological adaptation, and register; and
- send conflicts back to vocabulary or grammar records.

### 3. Sentence epoch

- compose sentences from eligible vocabulary, phrases, and constructions;
- include script, romanization, segmentation, gloss, and translation notes;
- exercise the level's declared competencies;
- run exact, structural, and semantic conflict checks; and
- revise upstream records when composition exposes a weakness.

An epoch may repeat before advancing. Completeness and consistency are separate measurements, and both must improve.

## Gates between levels

A level advances only when:

- its required semantic domains and grammatical functions have reviewed coverage;
- canonical entries meet provenance requirements;
- required paradigms have no unexplained gaps;
- phrase and sentence composition succeeds without ad hoc rule invention;
- high-severity conflicts are resolved;
- regression examples still pass after revisions;
- narrative-engine tests appropriate to the level pass without ambiguous or silently changing participants;
- embedding and exact-search indexes match current record revisions; and
- a human approves the level report.

## Paragraph gate

Paragraph generation begins during D2 only after all of these are true:

- accepted rules exist for clause linking, reference continuity, tense/aspect or event framing, and discourse relations used by the paragraph;
- any narrative paragraph using the hybrid engine has accepted rules for foreground chaining, the event-to-consequence/habit transition, proximate/obviative scope, center shifts, and multiple obviatives;
- rich sentences can be composed without unresolved high-severity conflicts;
- dependency invalidation and selective re-embedding have been demonstrated;
- at least one paragraph plan can be expressed entirely through canonical or explicitly reviewed dependencies; and
- a human authorizes paragraph work.

R1 expands paragraphs only after the D2 paragraph pilot is reviewed.

## Evaluation in every epoch

Reports track at least:

- coverage by sense, grammatical function, level, source lect, and register;
- cross-domain use of both co-parent continuities without imposing a mechanical quota or semantic silo;
- canonical/candidate/rejected counts;
- source and license completeness;
- exact duplicates and semantic near-duplicates;
- unresolved conflicts by severity;
- dependency invalidations;
- compositional test results;
- narrative-engine results: foreground progression, weqatal-frame transition, participant recovery, center-shift recovery, and ambiguity failures;
- retrieval quality; and
- continuity with active creative anchors, including documented reasons for departures; and
- API calls, token usage where available, and estimated cost.

## Spend gate

Phase 0 authorizes one small paid embedding smoke test. The test should use the least material needed to prove indexing, querying, model/fingerprint metadata, and stale-vector detection. The project then stops paid API activity and returns to the owner before any expanded embedding, generation, or evaluation run.

The smoke test is recorded in [`reports/embedding-smoke-2026-07-12.json`](reports/embedding-smoke-2026-07-12.json). Budget scenarios for a substantial first corpus are in [Initial-Build Budget](initial-build-budget.md). Neither document authorizes the proposed larger spend.
