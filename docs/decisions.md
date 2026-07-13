# Decision Record

This file records foundation decisions in a compact form. A decision remains active until a later entry explicitly supersedes it.

## Adopted decisions

### D-001 — Fresh canonical corpus

**Decision:** The active canonical corpus starts empty. Inherited translations, vocabulary, paradigms, and generated notes are not imported as canonical records. Creative-anchor wording is preserved as revision input, not canon.

**Reason:** The legacy corpus is circularly generated, inconsistently sourced, and internally contradictory.

### D-002 — Authority order

**Decision:** Authority descends from `language-goals.md`, then adopted decisions, then accepted sections of `language-spec.md`, then canonical structured records. Derived indexes and generated output have no normative authority.

### D-003 — Algonquian source hierarchy

**Decision:** Munsee Delaware / Lunaape is the regional Algonquian anchor. If it cannot meet a documented need, research checks responsibly sourced Mahican/Mohican and Lenape material first. Explicitly labeled Algonquin, Ojibwe, Mi'kmaq, Penobscot, or other Algonquian material may then fill a real gap after review. Nothing is silently mixed or relabeled.

**Revisit trigger:** Better community guidance, unavailable primary documentation, or evidence that a proposed feature depends on a different lect.

### D-004 — Exact attribution

**Decision:** “Algonquian” alone is not an acceptable lexical source label. Language, lect, source form, locator, and transformation are required for canon.

### D-005 — Honest formation history

**Decision:** Historical etymology, project formation process, and design alignment are separate fields. A coinage may be canonical without pretending to have a historical lineage.

### D-006 — Human-only canon

**Decision:** Only an authorized human reviewer may set `canonical` status. Automation may create candidates, evaluations, and recommendations.

### D-007 — Structured truth, derived embeddings

**Decision:** Revisioned structured records are authoritative. Embeddings and search documents are replaceable derivatives linked to record ID, record revision, model, dimensions, and content fingerprint.

### D-008 — Project proficiency levels

**Decision:** Use N1, N2, D1, D2, and R1 as project-specific coverage levels. They are not CEFR claims. Each level proceeds through vocabulary, phrases, and sentences; paragraph work is gated after rich sentence work.

### D-009 — Cultural guardrails

**Decision:** Do not auto-generate sacred, ceremonial, medicine, or community-restricted material. Do not use source-language stereotypes to allocate semantic domains. Fictional history must be labeled as fiction.

### D-010 — API spend boundary

**Decision:** One small live embedding smoke test is permitted. After it, all paid API work stops until the project owner reviews behavior, usage, and estimated cost and explicitly approves expansion.

### D-011 — Legacy archival references

**Decision:** Historical material is normally recovered through Git archive tags rather than kept in the active language tree. The two explicitly designated creative-anchor songs are the documented exception. See `legacy-audit.md` for exact references.

### D-012 — Explicit alternate-history premise

**Decision:** The setting imagines that Judea does not fall, a culturally rich Judean community crosses the Atlantic and settles in the Hudson/Mahicanituck Valley, and long contact develops through pidgin and nativized-creole stages into an increasingly elaborated community language. Hebrew culture is preserved and transformed. This is worldbuilding, never claimed history; the creole stage is itself understood as a full language.

### D-013 — Hebrew/Judean co-parentage

**Decision:** Judean/Hebrew continuity is a full co-parent, not a thin superstrate. Modern/common Hebrew is important for ordinary life; Biblical and Classical Hebrew are important narrative and literary resources. Hebrew may contribute lexicon, morphology, syntax, and discourse across domains.

### D-014 — Active creative anchors

**Decision:** [*We Walk Well* and *When the Lights Learn Our Names*](../references/creative-anchors/README.md) remain active creative anchors. Their exact wording, themes, voice, imagery, registers, and expressive ambitions are protected revision input. Individual forms and analyses remain reviewable.

### D-015 — Required hybrid narrative engine

**Decision:** A defining expressive capability combines an adapted Biblical Hebrew wayyiqtol foreground event chain, an adapted weqatal consequence/habitual frame, and Algonquian-inspired proximate/obviative participant tracking. Their interaction must support fast multi-participant narration, controlled discourse-center shifts, and an event-to-enduring-pattern transition. This capability is required even though its final forms and paradigms remain under research.

**Boundary:** The project must cite historical-source claims and describe the resulting construction as a deliberate conlang adaptation. A single obviative marker cannot be credited with uniquely identifying several participants without additional grammar or context.

### D-016 — Bounded N1 retrieval checkpoint

**Decision:** After reviewing the foundation smoke result, the owner authorized one fixed embedding evaluation over 20 N1 candidate records and five frozen paraphrase queries. The run had to use `text-embedding-3-small` at 256 dimensions, one provider request, the persistent budget ledger, and a sanitized report. The authorization is now consumed and the paid gate is disabled again.

**Result:** The successful call used 10,407 input tokens, cost approximately $0.000208 at the configured rate, and met its predeclared recall@3 sanity criterion. One preceding sandboxed attempt ended with `APIConnectionError` and no provider response; billing is unknown, so its full reservation remains conservatively counted. The local ledger therefore accounts for at most 58,102 tokens or $0.00116204. This checkpoint does not authorize paid generation, validate the candidate language, or establish an unbiased retrieval benchmark.

### D-017 — First bounded N1 core lexical checkpoint

**Decision:** Retain the source-first record architecture and build one bounded
candidate slice from 25 manually reviewed Hebrew items and 35 individually
cited Moraviantown Munsee items. Regional forms use the reversible pointed
`omeara_hebrew_transport` profile, which is analytic and noncanonical. Add 12
revision-pinned composition regressions without declaring new productive
grammar. After all local gates pass, permit one fixed embedding request over the
resulting 92 records and 12 frozen queries.

**Result:** The request used 50,922 input tokens at an estimated cost of
$0.00101844. All 12 intended records ranked first. A stricter final source audit
then corrected four lexical records and refreshed four dependent compositions;
fingerprint checks mark those eight vectors stale, and the paid call was not
repeated. The gate is disabled again. This result does not promote any record,
establish an unbiased benchmark, or authorize another API call. Current
community-connected guidance remains a blocker for canonical Munsee-derived
spelling and systematic source extraction.

## Open decisions

These do not block documentation, schema work, local fixtures, or an explicitly authorized bounded retrieval checkpoint. They do block canonical content that depends on them.

1. Canonical English name and endonym; whether *Djudeo-Mahikanítakh* is retained as a transparent coinage.
2. Complete source phoneme inventory and the precise Munsee/Mahican relationship used by the conlang.
3. Canonical romanization and Hebrew grapheme mappings, including vowel length and reduced vowels.
4. Exact conventions within Modern/common, Biblical, Classical, rabbinic, liturgical, regional, and diaspora Hebrew material, including how contact transforms them.
5. Exact implementation of the required narrative engine: wayyiqtol- and weqatal-derived forms, participant marking, center shifts, multiple-obviative handling, and interaction with ordinary tense/aspect.
6. Inclusive/exclusive distinctions, nominal classes, locatives, and direct/inverse paradigms outside that engine.
7. Source permissions or licenses for any material considered for systematic extraction.
8. Quantitative coverage thresholds for each proficiency level after initial measured epochs.
9. Whether any community-specific ceremonial vocabulary is necessary to the project at all.

## Decision procedure

A new decision records the question, evidence, alternatives, chosen outcome, consequences, reviewer, date, and any records invalidated. Material changes receive a new decision ID; earlier text is not silently rewritten to make the history look unanimous.
