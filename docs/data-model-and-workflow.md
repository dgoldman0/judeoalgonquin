# Data Model and Workflow

This document defines the conceptual authority and lifecycle of language records. Machine schemas implement it; they do not replace it.

## 1. Authority layers

The project has four distinct layers:

1. **Foundation documents** — goals, specification, policy, and decisions.
2. **Structured records** — the authoritative language knowledge base.
3. **Derived artifacts** — search documents, embeddings, indexes, reports, and exports.
4. **Generated output** — proposed translations and prose assembled from the first three layers.

Only the first two layers can define canon. An embedding vector, nearest-neighbor result, model response, or exported file is never authoritative.

## 2. Record families

The conceptual knowledge base needs these families:

- `lexeme` — a form and one or more senses;
- `morpheme` — an affix, clitic, stem-forming element, or grammatical marker;
- `construction` — a productive morphological, syntactic, or discourse rule;
- `phrase` — a reusable non-sentential combination;
- `sentence` — a complete reviewed utterance;
- `paragraph` — linked sentences with discourse structure;
- `creative_anchor` — protected source wording, themes, voice, imagery, and expressive constraints that revisions must address;
- `source` — bibliographic, community, contributor, and license metadata;
- `decision` — a machine-linkable design decision; and
- `evaluation` — a reproducible test, judgment, or conflict report.

Vocabulary, phrase, sentence, and paragraph are not merely different text lengths. Each has different dependency and evaluation requirements.

Creative anchors are neither canon nor disposable prompts. Their source wording remains preserved while proposed language revisions become separate, dependency-linked records.

The executable `schema/entry.schema.json` currently covers the language-bearing families `lexeme`, `morpheme`, `construction`, `phrase`, `sentence`, and `paragraph`. The source registry remains in `references/sources.yaml`; foundation decisions remain in Markdown; creative anchors remain preserved Markdown; and evaluations are executable tests or reports. None of those separate stores may be moved into entry JSONL until a dedicated schema and migration are added. This boundary is intentional and prevents the implementation from claiming record support it does not yet provide.

## 3. Common record fields

Every language record has:

- a stable, opaque ID that does not encode a mutable spelling;
- record family and schema version;
- lifecycle status;
- proficiency level;
- register and usage constraints;
- created and updated timestamps;
- creator and reviewer provenance;
- revision number;
- source links and confidence;
- dependency IDs;
- conflict and supersession links; and
- a human-readable change note.

Records that contain language forms also carry, as applicable:

- Hebrew script;
- canonical romanization;
- analytical segmentation;
- morpheme gloss;
- English lemma or translation;
- distinct sense IDs;
- part of speech or construction class;
- grammatical features;
- literal and idiomatic translations;
- historical etymology;
- formation process;
- design alignment;
- translation and grammar notes; and
- normalized text used for exact matching.

Lexical and morphemic records may also carry a typed lexical layer:

- `donor_candidate` preserves a reviewed source ingredient but is not itself a language word;
- `direct_contact_inheritance` records a source item after explicit contact adaptation or reviewed retention;
- `contact_native_formation` records a new internally formed word with revision-pinned inputs; and
- `learned_literary_reborrowing` is reserved for a deliberately less-adapted later Hebrew re-entry.

A donor and its contact output may share a surface form only when the contact record depends on that exact donor revision. This is an evidence/language overlay, not an undeclared homonym.

Empty fields are explicit. “Unknown,” “not applicable,” and “not yet researched” must not be conflated.

## 4. Lifecycle

The core statuses are:

- `draft` — incomplete working material;
- `candidate` — structurally valid and ready for checks;
- `reviewed` — examined by a human, with the review outcome recorded;
- `canonical` — approved by an authorized human reviewer;
- `deprecated` — retained for history but discouraged;
- `superseded` — replaced by identified record(s); and
- `rejected` — considered and excluded, with a reason.

Automation may create `draft` or `candidate` records and attach evaluations. It may not set `canonical`, including when every automated check passes. Canon promotion records the human reviewer and decision.

Canonical records are not edited in place without a revision event. Meaningful changes increment the revision, identify affected dependencies, and trigger review and re-indexing.

## 5. Candidate workflow

For each proposed record:

1. define the intended sense, level, and register;
2. retrieve exact and semantically related existing records;
3. gather source evidence under the provenance policy;
4. construct the proposal and document its transformation;
5. validate normalization, required fields, references, and dependency existence;
6. run deterministic grammar and consistency checks;
7. compare it with near neighbors for duplicate senses, spelling collisions, incompatible morphology, and conflicting notes;
8. generate compositional examples only from eligible dependencies;
9. record human review; and
10. promote, revise, defer, or reject it.

An entry may be useful and well formed yet remain a candidate because its source, paradigm, or cultural context is incomplete.

## 6. Composition requirements

A phrase references the lexemes, morphemes, and construction records it uses. A sentence references its component records and supplies a full gloss. A paragraph additionally records discourse relations and participant continuity.

Narrative records using the hybrid engine additionally identify:

- the wayyiqtol- or weqatal-derived construction record used by each relevant clause;
- foreground, background, consequence, habitual, or standing-pattern function as applicable;
- participant IDs and their proximate/obviative status at each clause;
- any discourse-center shift and how it is licensed;
- how multiple obviatives remain distinguishable; and
- the point and interpretation of any transition from event chain to consequence or recurring pattern.

If a dependency changes, downstream records become review candidates. They do not silently inherit the new form.

[*We Walk Well* and *When the Lights Learn Our Names*](../references/creative-anchors/README.md) are the initial `creative_anchor` sources. Their themes, voice, narrative aims, and existing wording are continuity constraints. A revision may change any individual form after review, but it must retain a link to the anchor, explain material departures, and never overwrite the preserved source text.

## 7. Retrieval and embeddings

The initial executable index combines:

- exact normalized lookup;
- status filtering;
- semantic similarity over derived search documents.

Individual English glosses, pointed and unpointed Hebrew, romanization, and declared variants are stored as exact aliases. Full record-family, level, register, source-lect, and grammatical-feature filters plus dependency/reverse-dependency traversal are planned index extensions; callers must not assume they exist yet.

An embedding search document may include the form, sense, gloss, formation rationale, grammar notes, and carefully selected dependency context. It must include the record ID and revision so stale vectors can be detected.

Embeddings are regenerated only for changed records and any derived documents whose content changed. Switching embedding models creates a separately identified index; it does not rewrite language records.

Similarity is a discovery signal, not proof of equivalence or conflict. Every suggested duplicate or contradiction must be resolved through structured evidence and review.

Donor candidates remain searchable for research, but generation should prefer contact-language layers. Until layer filtering is implemented in the index, callers must inspect `metadata.lexical_layer` rather than treating every lexical search result as usable output.

## 8. Conflict handling

Conflicts are first-class records or evaluations. Useful categories include:

- duplicate form with unintended sense collision;
- competing form for the same sense;
- incompatible source attribution;
- orthographic inconsistency;
- paradigm gap or contradiction;
- register mismatch;
- circular example or unsupported derivation;
- cultural-policy concern; and
- stale downstream dependency.

Resolution links all affected records and preserves the rejected or superseded reasoning.

## 9. Reproducibility and cost

Every generation or embedding run records its input record revisions, model identifier, parameters, output artifact fingerprint, and failure state. Secrets and raw API credentials are never stored.

The first live embedding operation was limited to one small smoke test over
noncanonical fixtures. Separately authorized checkpoints then embedded the
20-record architecture probe with five queries and the 92-record N1 core with
12 queries. Their committed reports act as persistent consumed markers.
Further live embedding or semantic-search operations require `--live`, a new
explicit owner authorization, an enabled `config/api-budget.json`, per-run
caps, a cumulative token cap, and an ignored local reservation/usage ledger.
Reservations are written before network access so a crash or uncertain failure
cannot silently invite an unaccounted retry.

The first contact-synthesis pass made no API request. Its donor-layer typing,
revision propagation through dependent probes, and 15 new contact records
correctly leave all 107 records stale or missing in the local checkpoint index.
A dry-run estimates about 64,703 record-input tokens, or roughly $0.00129 at
the configured embedding rate, for a full refresh; that
estimate is not authorization.
