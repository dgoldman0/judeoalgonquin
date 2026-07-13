# Contact Phonology and Lexical Formation

**Status:** The architecture and evidence boundaries in this document are accepted for current work. The sound mappings and formation rules are proposed candidates. They may generate noncanonical records and tests; they do not establish canon.

## 1. What the current records mean

The first source-first lexical checkpoint is an ingredient inventory, not a finished contact lexicon. Its Hebrew and Moraviantown Munsee records preserve individually reviewed forms, senses, categories, and source cautions. A source form does not become a Judeo-Algonquin word merely because the database can display it in Hebrew script.

Language records now distinguish four lexical layers:

1. `donor_candidate` — exact or normalized source material under consideration; never canonical language by itself;
2. `direct_contact_inheritance` — a source item that has passed through the shared contact filter, even when that filter leaves its surface form unchanged;
3. `contact_native_formation` — a new word built inside the project from reviewed contact-language inputs and an explicit formation rule; and
4. `learned_literary_reborrowing` — a later, deliberately less-adapted Hebrew re-entry for learned, historical, or literary use.

This separates evidence from design without hiding the evidence. A contact record depends on the exact donor record revisions it uses, while the donor forms and source locators remain recoverable and searchable.

Classifying a donor is a real record revision. Dependency pins are propagated through the existing construction, phrase, and sentence probes, so the local embedding index correctly treats every affected record as stale rather than concealing an architectural change behind an unchanged revision number.

## 2. Provisional shared sound inventory

The first contact probe uses this deliberately conservative inventory:

- stops: `p b t d k g`;
- affricates: `c` /ts/ and `č` /tš/;
- fricatives: `f v s z š x h`;
- nasals: `m n`;
- liquids: `l r`;
- glides: `w y`;
- short vowels: `a e i o u ə`; and
- inherited regional long vowels: `aa ee ii oo`.

`c` and `č`, `v` and `w`, and short and long vowels remain distinct. Productive `uu` is not proposed yet because the reviewed regional sample does not establish it. Source-licensed clusters remain lexical exceptions; the project does not delete unfamiliar segments merely because they are absent from a small sample.

The Academy of the Hebrew Language describes contemporary Hebrew with the five vowel qualities `a e i o u`, while also warning that the Tiberian pointing system and current pronunciation reflect different historical traditions. Its general transliteration guidance is pronunciation-oriented. Those facts justify keeping exact Hebrew spelling in source evidence while treating the contact romanization as a separate design result; they do not reconstruct the speech of the fictional community. See the Academy's [orthography overview](https://eng.hebrew-academy.org.il/our-work/language-decisions/orthography/), [historical overview](https://eng.hebrew-academy.org.il/overview-of-hebrew/), and [transliteration overview](https://eng.hebrew-academy.org.il/our-work/language-decisions/transliteration/).

## 3. Ordinary Hebrew contact filter

For ordinary Hebrew-derived lexical input, the first probe applies these operations:

- write /š/ as `š`, /x~χ/ as `x`, and /y/ as `y`;
- merge ordinary `ח` and fricative `כ` as contact `x`, while preserving the exact source letter in evidence;
- realize ordinary `ק` as `k`;
- do not preserve source gemination as an ordinary contact contrast;
- omit a nonpronounced final `ה` and word-edge laryngeals from the contact romanization;
- do not manufacture a vowel from every written sheva; and
- pilot word-final Hebrew-source `/v/` as contact `w` in the three reviewed items `aw`, `xalaw`, and `lew`, without generalizing the change to onset or intervocalic `v`.

Thus contact `lexem` comes from source `לֶחֶם`, `xalaw` from `חָלָב`, `pri` from `פְּרִי`, and `katan` from `קָטָן`. These are transparent project adaptations, not invented historical attestations.

The data model does not yet store contact stress. When that field is added, direct inheritance must initially preserve source lexical stress item by item until a larger collision study supports regularization. This caution is especially important because the Academy notes that stress can distinguish ordinary `וְ־` plus a perfect form from some weqatal forms. The ordinary lexical filter must therefore never be applied mechanically to the future narrative morphology. See the Academy's [discussion of narrative waw and stress](https://hebrew-academy.org.il/%D7%95-%D7%94%D7%94%D7%99%D7%A4%D7%95%D7%9A/).

## 4. Regional contact filter

The regional input retains `ə`, `š`, `č`, `x`, `w`, inherited clusters, and doubled vowel length. The scholarly source's hyphens remain in `segmentation`, but a fully lexicalized fixed noun does not display internal analytical hyphens in its surface form. The first affected forms are:

- `ootee-n-ay` → `ooteenay`;
- `apii-n-ay` → `apiinay`;
- `weent-akwiiwan` → `weentakwiiwan`;
- `wiisak-ii-m` → `wiisakiim`;
- `pak-ii-nčəw` → `pakiinčəw`; and
- `tiih-ii-nčəw` → `tiihinčəw`.

The segmentation and source form remain unchanged in their analytical fields. Bound TA/TI stems remain bound and class-specific. The source's conditioned deletions, contractions, epentheses, and vowel changes do not become general Judeo-Algonquin rules merely because they occur in the dissertation.

## 5. New-formation phonotactics

An inherited word or reviewed inherited morpheme retains its source-licensed shape even inside a new formation. The candidate template `(C)(w/y)V(V)(C)` governs only phonological material newly supplied by the contact grammar and boundary repair; it does not dismantle inherited `pr-` in `pri` or `nč-` in `-nčəw`. At a newly created vowel boundary, insert `y` only when an explicit contact record calls for hiatus repair. Do not automatically delete final `w`, shorten long vowels, reduce every unstressed vowel, or simplify a licensed cluster.

For genuinely new formations, the stress test under consideration is weight-sensitive: long vowels and closed syllables are heavy; choose the rightmost heavy syllable among the final two, otherwise the penult. This is a testable hypothesis, not an accepted rule. If stress becomes a modeled field, inherited source stress will initially outrank this new-formation default.

## 6. Formation grammar

The initial lexical grammar is right-headed:

`ROOT + CATEGORY-BEARING FINAL → lexical noun`

The final determines the output category and source-informed nominal class. Every hybrid proposal must identify its head, the semantic contribution of each input, boundary behavior, dependency revisions, rejected host types, and why the result fills a real contact-language need. Hebrew grammatical gender never maps mechanically to regional animacy, and a Munsee TA/TI pair never becomes two loose synonyms.

One successful mixed word does not establish productivity. A formation pattern may be called productive only after it has, at minimum:

- three independently reviewed successful hosts drawn across both lexical parent strata;
- both a vowel-final and a consonant-final host;
- an explicit head and output class;
- at least one rejected host with a stated failure reason;
- stable phonological and orthographic boundary behavior; and
- regression tests that fail when those constraints are violated.

Until then, each mixed form is an isolated `contact_native_formation` candidate. Calques are reserved for genuinely structured meanings—idioms, relational expressions, discourse constructions, or analyzable compounds—not for relabeling a basic single lexeme.

Sources cited by the component records support those components, not the newly coined mixed sense. A mixed record therefore links its revision-pinned inputs through `formation` and `relations`; it does not copy component citations into `source_evidence` and falsely claim that a source attests the coinage.

## 7. Lexical allocation and doublets

Contact synthesis includes semantic allocation, not only sound change. The first audit keeps `adam` for human/person beside regional `lənəw` for man. It proposes source-supported `iša` for wife/spouse while `oxkweew` remains the regional donor candidate for “woman”; a separate contact-inheritance record for that sense still requires review. A doublet is admitted only when its difference in sense, register, construction, or discourse behavior is documented; unmotivated duplicates remain conflicts.

## 8. Narrative firewall

The ordinary contact filter does not define the wayyiqtol–weqatal–obviation engine. Lexical and ordinary-clause work reserves the following order of possible functions without inventing their morphology:

`CHAIN/FRAME – CENTER SHIFT – NEG/TAM – PREVERB – ROOT – FINAL/THEME – PERSON/NUMBER – OBVIATION`

Ordinary coordination must remain distinct from foreground-chain and consequence-frame linkers. A sound rule may not erase participant marking or the stress/morphology needed to distinguish the two Biblical-Hebrew-derived narrative constructions. The engine remains governed by [Hybrid Narrative Engine](narrative-engine.md).

## 9. What the first synthesis probe can prove

The first probe may prove that:

- one shared pointed-script profile round-trips all declared contact sounds;
- donor candidates and language candidates are structurally distinct;
- direct Hebrew and regional inputs pass through explicit, reproducible contact decisions;
- semantic collisions can be resolved deliberately; and
- two mixed formations can preserve head, source, dependency, and uncertainty information.

It cannot prove that the inventory is final, that either mixed final is productive across the language, that the forms represent real alternate history, that source inflection transfers, or that the narrative engine has been implemented.
