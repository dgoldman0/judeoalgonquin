# Language Specification

**Relationship to goals:** This document implements [Language Goals](language-goals.md). It cannot override them.

## Status markers

- **[ACCEPTED]** — normative for current work.
- **[PROPOSED]** — a design target or candidate rule; it must not be assumed in canonical entries.
- **[DEFERRED]** — intentionally unresolved until prerequisites exist.
- **[REJECTED]** — excluded from current work even if it appeared in inherited material.

## 1. Identity and representation

**[ACCEPTED] Constructed status.** The language is intentionally constructed. Its explicit worldbuilding premise is a continuing Judean civilization whose people cross the Atlantic after Judea does not fall, settle in the Hudson/Mahicanituck Valley, and develop a pidgin and then a nativized creole that continues to elaborate through long contact. This is not claimed history, and “creole” is not used to imply an incomplete language.

**[ACCEPTED] Co-parent continuity.** Judean/Hebrew and regional Algonquian language and culture are co-parents. Hebrew is a living, changing continuity across ordinary and literary life, not merely a script, connective layer, or thin superstrate.

**[ACCEPTED] Paired representation.** Every canonical form must have:

- a Hebrew-script form;
- a canonical romanization;
- Unicode-normalized storage; and
- an analytical form with morpheme boundaries when the entry is morphologically complex.

**[ACCEPTED] Unicode normalization.** Stored text uses NFC. Normalization must not silently change a form's reviewed spelling; validation reports any difference.

**[PROPOSED] Working names.** “Judeo-Algonquin” is the project title. The language's canonical English name, endonym, and the status of *Djudeo-Mahikanítakh* remain open decisions.

## 2. Phonology and orthography

**[ACCEPTED] Hebrew script.** Hebrew script is the primary display script. Pointed forms are permitted for teaching, disambiguation, dictionaries, and literary presentation.

**[ACCEPTED] Romanization as data, not decoration.** Romanization must be stored directly and validated. It may not be reconstructed from visual guesswork when the Hebrew spelling is ambiguous.

**[PROPOSED] Abjad-plus-matres design.** Running text may use matres lectionis, with niqqud optional by register. Exact mappings are not yet accepted.

**[PROPOSED] Contact-probe inventory.** The first synthesis probe uses the shared consonants `p b t d k g c č f v s z š x h m n l r w y`, short vowels `a e i o u ə`, and regional-source long vowels `aa ee ii oo`. Its ordinary Hebrew adaptation, regional retention rules, phonotactic boundaries, and productivity gates are defined in [Contact Phonology and Lexical Formation](contact-phonology-and-formation.md). This inventory is executable and testable but noncanonical.

**[PROPOSED] Pointed contact profile.** `contact_pointed_candidate` is a reversible fully pointed teaching and database profile for the proposed contact inventory. Its unpointed alias is deliberately lossy. It does not settle the later choice among phonemic, etymographic, and morphographic running-text spelling.

**[DEFERRED] Canonical inventory and grapheme mapping.** Community-connected review, broader collision tests, stress evidence, and comparison with responsibly sourced Mahican/Mohican and Lenape material remain necessary before the inventory or running-text grapheme system can become canonical.

**[ACCEPTED] Boundary distinction.** Database segmentation uses `-` between morphemes. Hebrew maqaf, geresh, spaces, and punctuation are orthographic choices and must not be used as the only record of morphological structure.

**[REJECTED] Legacy frequency as authority.** Variants such as `-ink`/`-ənk` or multiple spellings of the same legacy word are not accepted allomorphs until a rule accounts for them.

## 3. Source-layer architecture

**[ACCEPTED] Donor/language separation.** A documented source form is a `donor_candidate`, not automatically a Judeo-Algonquin word. Actual language proposals are separately dependency-linked as `direct_contact_inheritance`, `contact_native_formation`, or later `learned_literary_reborrowing`. A donor candidate cannot become canonical as language material.

**[ACCEPTED] Exact lect attribution.** Each borrowed or adapted item names a specific source lect. Generic “Algonquian origin” is insufficient.

**[ACCEPTED] Algonquian source path.** Munsee Delaware / Lunaape is the regional anchor. When it cannot supply a documented need, research looks first to responsibly sourced Mahican/Mohican and Lenape material. Explicitly labeled Algonquin, Ojibwe, Mi'kmaq, Penobscot, or other Algonquian material may then fill a real gap after review. Nothing is silently mixed or relabeled as Munsee.

**[ACCEPTED] Hebrew stratum labels.** Hebrew-derived entries identify their period or register when it matters to form or use. Modern/common Hebrew is important ordinary-life material; Biblical and Classical Hebrew are important narrative and literary material.

**[ACCEPTED] Cross-domain parentage.** Hebrew and source-specific Algonquian material may each contribute vocabulary, morphology, syntax, and discourse across semantic domains. Neither is restricted to a predetermined list of cultural functions.

**[PROPOSED] Functional integration.** The language is expected to combine a productive Hebrew continuum with substantial source-specific Algonquian predicate, relational, derivational, and discourse structure. Exact interactions remain subject to evidence and usability tests; they must not be described through a simple superstrate/substrate split.

**[REJECTED] Capacity stereotypes.** There is no rule that abstractions must be Hebrew or that concrete and natural concepts must be Algonquian.

## 4. Morphology

**[ACCEPTED] Paradigm requirement.** A productive affix or inflectional rule cannot become canonical from a single illustrative form. Its record must specify:

- source and source category;
- host classes;
- full distinctions relevant to the rule;
- ordering and allomorphy;
- phonological or orthographic effects;
- counterexamples or restrictions; and
- at least one reviewed compositional test.

**[PROPOSED] Ordinary AI participant marking.** The current closed candidate
retains seven independent-order person-number distinctions on `apii-` “be
located,” `ləmatapii-` “sit,” and `niipawii-` “stand”: first, second, and third
singular; inclusive and exclusive first plural; second plural; and third
plural. It regularizes the contact surfaces transparently, requires `-m` in the
first- and second-singular cells, and suspends source contraction, insertion,
W-shift, and deletion rules. This is not yet a general AI paradigm and carries
no tense, aspect, modality, obviation, or narrative status.

**[PROPOSED] Closed static locative.** Contact `-ənk` is admitted only on six
listed hosts: regional `aanay`, `mohkaməy`, and `apiinay`, plus Hebrew-derived
`bayit`, `xeder`, and `šulxan`. Exact-source road and ice contractions are
preserved; the bed and consonant-final Hebrew-host forms are explicit contact
regularizations. The construction expresses a general static location and does
not license goals, sources, paths, direction, attachment to new hosts, or a
general interaction with Hebrew prepositions.

**[PROPOSED] Nominal classes and animacy.** A source-informed classification system may affect agreement, plural marking, and discourse. Classification cannot be assigned through invented claims such as an object being “alive” unless that is explicitly adopted as a new conlang rule rather than presented as source-language fact.

**[PROPOSED MECHANICS; ACCEPTED CAPABILITY] Obviation and participant tracking.** A proximate/obviative system is required for the hybrid narrative engine. Its implementation must document marking, agreement, scope, center shifts, and what happens with more than one obviative. One binary marker must not be claimed to uniquely identify several participants by itself.

**[PROPOSED] Direct/inverse alignment.** A deliberately adapted system may be developed only after its participant hierarchy and morphology are explicit. “An inanimate subject acts on an animate object” is not an accepted definition of inverse.

**[PROPOSED] Productive compounding and incorporation.** Hebrew and source-Algonquian stems may enter reviewed formation patterns. Each pattern requires directionality, head rules, phonological adaptation, and register constraints.

**[PROPOSED] Hebrew-derived morphology in ordinary use.** Reviewed Hebrew inflectional and derivational material may remain productive or be transformed by contact across ordinary vocabulary as well as literary registers. Each pattern requires the same full-paradigm and interaction evidence as an Algonquian-derived pattern.

**[PROPOSED] Limited perception Absolute.** The current N1 candidate preserves
six class-sensitive TA/TI perception stems and supplies inclusive and exclusive
first-plural cells only. A predicate must precede one overt indefinite admitted
object: `adam` is animate-class, while `or`, `kol`, and `aanay` are
inanimate-class in this construction. Contact `a` in the TA cells and `o` in
the TI cells are explicit project abstractions from two cited source examples,
not claimed detachable Munsee morphemes. The construction does not license
object omission, attentive “listen,” other persons, direct/inverse behavior,
obviation, or narrative morphology.

**[REJECTED] Legacy pseudo-paradigms.** The old uncited `nə-/kə-/wə-` tables,
singular/plural collapses, and unattested suffix stacking are not imported as
rules. This does not reject the separately sourced, bounded, seven-cell AI
candidate above.

## 5. Syntax and discourse

**[PROPOSED] Predicate prominence.** Neutral clauses are expected to permit predicate-prominent structure and omitted independent pronouns when agreement makes reference clear.

**[PROPOSED] Information-structural flexibility.** Constituent order may respond to topic, focus, animacy, and discourse status. “Free word order” is not an adequate rule; constraints must be documented from accepted examples.

**[PROPOSED] Hebrew connectives and subordination.** Reviewed Hebrew-derived conjunctions, relativizers, complementizers, and discourse particles may frame predicates from the adapted Algonquian layer.

**[PROPOSED] Static location clauses and questions.** An admitted finite AI
location or posture predicate precedes one of the six listed locative phrases.
A lexical third-person subject precedes that predicate; indexed first and
second persons need no independent pronoun in the tested clauses.
Hebrew-derived contact `efo` occurs clause-initially and asks only static
“where?” It does not yet license a general interrogative system, relative
“where,” “wherever,” “where to,” or “where from.”

**[PROPOSED] Ordinary nominal coordination.** Contact proclitic `wə-` attaches
to the second of two admitted nouns. Current contact phrases use the separate
contact-layer morpheme and construction, which revision-pin the Hebrew donor
evidence; the donor record itself is not a finished contact-language word.

**[PROPOSED] Ordinary finite coordination.** Contact proclitic `wə-` may join
two complete affirmative first-plural clauses when their clusivity agrees. It
attaches to the second clause and contributes ordinary coordination only. It
does not contribute sequence, consequence, recurrence, tense, aspect,
foregrounding, center shift, wayyiqtol, or weqatal behavior.

**[ACCEPTED CAPABILITY] Hybrid narrative engine.** The language must support the combined wayyiqtol–weqatal–obviation behavior defined in [Hybrid Narrative Engine](narrative-engine.md). This is a central expressive requirement rather than an optional ornament or three independent feature ideas.

**[PROPOSED MECHANICS] Wayyiqtol-derived foreground chain.** A dedicated narrative construction should advance reference time through a foregrounded sequence of events. Its forms, allowable predicates, interruption behavior, and relationship to ordinary tense/aspect remain to be established from cited Biblical Hebrew evidence and explicit conlang adaptation.

**[PROPOSED MECHANICS] Weqatal-derived consequence frame.** A dedicated construction should allow a narrative to shift from particular events into designed prospective consequences, recurring responses, standing expectations, or enduring patterns. Those are project functions; the final specification must not present them as an exhaustive description of historical Biblical Hebrew weqatal.

**[PROPOSED MECHANICS] Chain and participant interaction.** Every foregrounded narrative clause must make its participant interpretation recoverable through overt nouns, agreement, proximate/obviative status, or a documented combination. Center shifts must be marked or constrained. Multiple obviatives require more information than one shared binary marker.

**[DEFERRED] Everyday tense, aspect, and modality.** No complete system is accepted. The final design must explain how lexical aspect, inflection, particles, and discourse constructions interact.

## 6. Registers

**[ACCEPTED] Register labels are required when they license different structures.** Initial working registers are:

- `ordinary` — conversation and practical prose;
- `careful` — edited explanatory and reference prose;
- `narrative` — storytelling that may license the hybrid wayyiqtol–weqatal–obviation engine;
- `literary` — narrative and poetic structures;
- `ritual_style` — constructed ceremonial or liturgical-style language, never represented as authentic community ritual.

**[PROPOSED] Register-specific complexity.** More elaborate morphology may occur in literary registers, but ordinary speech must remain grammatically coherent rather than being an arbitrary simplification.

## 7. Glossing and examples

**[ACCEPTED] Every normative complex example includes:** Hebrew script, romanization, segmentation, morpheme gloss, idiomatic English, record IDs for dependencies, register, and review status.

**[ACCEPTED] Examples do not prove their own rules.** A generated sentence cannot validate the grammar that generated it. Normative examples must use independently accepted components and pass review.

**[ACCEPTED] Creative-anchor continuity.** [*We Walk Well* and *When the Lights Learn Our Names*](../references/creative-anchors/README.md) remain active sources of themes, voice, wording, register, and expressive requirements. Proposed revisions must preserve their identity or explicitly document an intentional change. Their individual forms and grammatical commentary remain reviewable.

**[ACCEPTED] No inherited canon.** Fine-tuning-era words, phrases, sentences, and paragraphs do not become canonical through age or repetition. Apart from the songs' protected role as creative revision input, an old form can return only as a newly sourced and reviewed candidate.
