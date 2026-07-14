# Initial-Build Budget

**Estimate date:** 2026-07-12

**Status:** Planning estimate, not spending authorization. Pricing and assumptions must be rechecked before a bulk run.

## 1. What “decent initial build” means here

This estimate models a substantial first N1-oriented corpus rather than a token demo:

| Record family | Target |
|---|---:|
| Lexemes and productive morphemes | 600 |
| Phrases | 400 |
| Sentences | 400 |
| Constructions plus separately structured source/evaluation artifacts | 100 |
| **Total reviewed working units** | **1,500** |

Every language record is assumed to include source or formation metadata, Hebrew script, romanization, notes, dependencies, and review state. These counts are planning targets, not proficiency definitions or a commitment to accept 1,500 forms.

## 2. Measured embedding result

The one authorized live smoke test embedded three noncanonical fixture records plus one query in one request:

- model: `text-embedding-3-small`;
- dimensions: 256;
- billed input: 422 tokens;
- ranking: home lexeme, home-locative phrase, then path lexeme; and
- estimated charge at $0.02 per million input tokens: **$0.00000844**.

The sanitized result is committed at [`reports/embedding-smoke-2026-07-12.json`](reports/embedding-smoke-2026-07-12.json). Reduced dimensions lower local storage and comparison cost; embedding API charges remain based on input tokens.

An independent review immediately after the call expanded the entry schema and embedding projection to include stable senses, grammatical features, exact source evidence, and narrative analysis. The provider connection and semantic ordering were therefore tested live, while freshness invalidation and the richer projection are tested locally with deterministic fake vectors. The paid smoke was not repeated.

The owner then authorized a single richer N1 retrieval sanity test. Twenty candidate records and five frozen paraphrase queries were embedded together in one request at 256 dimensions:

- billed input: 10,407 tokens;
- estimated charge: **$0.00020814**;
- recall@1: 0.8;
- recall@3: 1.0; and
- mean reciprocal rank: 0.9.

One preceding sandboxed attempt ended with `APIConnectionError` and no provider response. Its billing status is unknown, so the ignored local ledger conservatively retains the entire reservation. Cumulative accounting is therefore at most 58,102 tokens or **$0.00116204**, while the successful provider response itself cost the amount above.

The sanitized report, including complete rankings and reproducibility hashes, is committed at [`reports/n1-pilot-embedding-evaluation-2026-07-12.json`](reports/n1-pilot-embedding-evaluation-2026-07-12.json). A final citation audit changed several source-grounding fields after the call; the report preserves both hashes, and the content-fingerprint gate now treats the live vectors as stale. The call was not repeated. Five project-authored queries have coarse 0.2 metric resolution, so this result establishes only that the bounded retrieval and invalidation pipeline behaves sensibly. It is not a language-quality evaluation or an unbiased benchmark.

The next owner-authorized checkpoint embedded the complete first bounded N1
core: 92 current records plus 12 frozen queries in one request.

- billed input: 50,922 tokens;
- estimated charge: **$0.00101844**;
- recall@1: 1.0;
- recall@3: 1.0; and
- mean reciprocal rank: 1.0.

The sanitized report is committed at
[`reports/n1-core-embedding-evaluation-2026-07-12.json`](reports/n1-core-embedding-evaluation-2026-07-12.json).
The final source comparison corrected four lexical records and refreshed four
dependent compositions after the call. The report preserves both manifests;
84 current vectors remain fresh and eight are deliberately stale. No paid retry
was made.

As of the 2026-07-12 N1 core checkpoint, all three successful checkpoints had
confirmed usage of 61,751 input tokens,
or approximately **$0.00123502**. Including the earlier connection failure at
its full conservative reservation gave that day's upper accounting bound
of 109,446 tokens, or **$0.00218892**. Paid access is disabled again.

The later 180-record static-place checkpoint added 108,422 confirmed input
tokens and followed a 476,172-token failed reservation that remains
conservatively counted. Current checkout-stable accounting is therefore
694,040 tokens, or **$0.0138808**, across four successful checkpoints and both
conservatively retained failures. This is accounting, not a claim that every
failed reservation was billed. Paid access remains disabled.

The structured corpus has since grown to 264 records, but the living semantic
snapshot remains at 180. No paid request was made while manually authoring the
45 motion/action or 39 domestic-action records. A dedicated frozen incremental
plan for the earlier motion tranche would embed 45 records plus 12 diagnostics
in one request. It estimates 34,692 input tokens, about **$0.00069384**, with a
deliberately conservative 140,321-token ceiling of **$0.00280642**. The 39
domestic embedding documents add about 103,940 UTF-8 bytes, roughly 25,985
tokens or **$0.00051970** before their own diagnostics. These figures show that
retrieval cost remains small; neither plan is spending authorization, and the
motion-only plan would still leave the newer domestic records absent.

For 1,500 richer records, initial indexing plus selective re-embedding over two major revision rounds is conservatively modeled as 1.2 million embedding tokens. At the current small-model rate, that is approximately **$0.024**. Even a much heavier 10-million-token embedding workload would be about **$0.20**.

## 3. Model-assisted proposal and review estimate

Content work dominates the cost. The planning envelope assumes two model passes per record:

| Pass | Assumed input | Assumed output | Corpus total |
|---|---:|---:|---:|
| Sourced proposal / composition | 1,800 tokens per record | 500 tokens per record | 2.70M input + 0.75M output |
| Conflict, provenance, and consistency review | 2,200 tokens per record | 350 tokens per record | 3.30M input + 0.525M output |
| **Total** |  |  | **6.00M input + 1.275M output** |

The envelope intentionally includes retrieved context and substantive notes. It does not assume that every generated candidate becomes canonical.

Using current published standard token rates:

| Generation/review model | Input / output per 1M tokens | Estimated language-work cost | Plus embeddings |
|---|---:|---:|---:|
| GPT-5.6 Luna | $1 / $6 | $13.65 | about $13.67 |
| GPT-5.6 Terra | $2.50 / $15 | $34.13 | about $34.15 |
| GPT-5.6 Sol | $5 / $30 | $68.25 | about $68.27 |

The balanced working recommendation is approximately 85% Terra for proposal and routine review, with 15% Sol reserved for difficult formation, narrative-engine, and conflict decisions. On the same token envelope this is about **$39.27 including embeddings**. A 25% allowance for rejected attempts, retries, and underestimation brings the proposed cap to **$50**.

## 4. Recommended spending gates

Do not authorize the whole estimate as one uncontrolled run.

1. **$5 checkpoint:** build and review a representative slice spanning Hebrew-derived ordinary vocabulary, regionally anchored Algonquian material, hybrid formations, phrases, sentences, and one narrative-engine micro-scene.
2. **$20 cumulative checkpoint:** expand only after retrieval, provenance, and consistency evaluations show that the workflow is improving accepted material rather than producing volume.
3. **$50 hard cap:** complete the modeled 1,500-record first build only if the earlier checkpoints pass. Stop before the cap and report actual usage if quality or source availability becomes the limiting factor.

Luna may be useful for mechanical classification or formatting after evaluation, but source-sensitive language decisions should not be assigned to it merely to reduce cost. Sol should be selective rather than the bulk default.

## 5. Exclusions and uncertainty

The estimate does not include:

- paid web-search or other tool-call fees;
- purchasing dictionaries, books, or permissions;
- human expert or community consultation;
- unusually long reasoning traces or provider retries;
- taxes or account-specific contractual pricing; or
- wholesale reprocessing after a major grammar redesign.

Prompt caching or batch processing may lower cost, but the budget does not depend on those savings. Current account credit and billing limits are not visible to this repository or CLI and must be checked in the OpenAI dashboard before authorizing the first $5 tranche.

## 6. Pricing references

- [OpenAI vector embeddings guide](https://developers.openai.com/api/docs/guides/embeddings)
- [`text-embedding-3-small` model page](https://developers.openai.com/api/docs/models/text-embedding-3-small)
- [Current model-selection guidance](https://developers.openai.com/api/docs/guides/latest-model)
- [GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna)
- [GPT-5.6 Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra)
- [GPT-5.6 Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol)
