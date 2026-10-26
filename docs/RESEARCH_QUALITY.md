# Research quality improvements

The local connection and citation checks work, but an exported real-source report showed why those checks alone are insufficient: a model can select an authentic quotation and still misread a quarter, unit, negation or financial implication.

## Implemented in this update

- **Structured financial context:** reported revenue, net income, diluted EPS and weighted-average diluted shares are copied from saved SEC facts. Every fact retains dates, units, currency, accession/source and reported/derived provenance. Two recent quarters, the latest annual period and TTM are displayed when available. Missing or incompatible values remain unavailable; no FX conversion or current-share estimate is invented.
- **Period/unit checks:** half-year cumulative values cannot enter a quarterly row. Unknown units, conflicting period starts, non-finite values, future-dated facts and invalid share counts are excluded. EPS stays in currency per share; share counts stay in individual shares.
- **Controlled numerical publication:** model-written statements matching financial-metric/number patterns are withheld from published claims and recorded by reason/hash. Financial numbers are shown in the structured table. This is a conservative heuristic, not a proof that every conceivable numerical phrasing is detected; it can also withhold valid statements for review.
- **Complete context:** evidence windows expand around full sentences rather than starting at arbitrary character offsets. Overlong/table-like sentences are omitted rather than cut into misleading fragments. This remains selective keyword-based retrieval, not complete document understanding.
- **Issuer linking:** an audited heuristic screens sources using the requested ticker, legal company name and optional explicit aliases. It excludes unlinked stories and third-party portfolio disputes without issuer exposure, while retaining a dispute for the named broker when appropriate. This applies to any supported ticker; no company-specific production rule is hardcoded. Mentions do not certify economic relevance, and product/subsidiary-only stories can be omitted without aliases.
- **Presentation and preservation:** the report and PDF show period-labelled unscaled financial facts and disclose withheld statements. Reanalysis preserves the original source snapshot/horizon and creates a new record after successful batch validation, preserving the old one.

## Evidence

- **214 backend tests** cover financial grounding, period/unit rejection, source linking across different issuers, context preservation, publication controls, PDF persistence, update integrity and build/code rollback.
- **14 controlled Chromium tests** pass, including the new financial report table and 320px overflow check. Production build and TypeScript pass.
- An offline check against the user-provided AAPL export preserves four structured financial periods, supplies the correct Q2 values, would withhold its incorrect numerical claim, excludes 11 unlinked/portfolio-dispute items, and restores the CEO transition date and full negation context in the selected windows.
- A controlled transport handoff applies the eight-file patch to the original Windows ZIP source and completes six batches with the provided saved sources. It creates a new record, withholds a deliberately injected bad numerical claim and preserves the original record/configuration. This test runs in the cloud with a controlled response, **not the user's Qwen**.
- Execution of this quality update on the user's Windows PC and semantic review of its new Qwen output are still pending. The earlier citation-reference correction did complete a real six-batch Windows run; it is separate evidence.

## What follows

1. **Review the same saved evidence after the update.** Check period/unit accuracy, executive-event context, source attribution, withheld statements and unresolved questions. Then repeat on several issuers/industries, including missing-data and foreign-currency cases. Report individual failures rather than assigning an arbitrary aggregate score.
2. **Strengthen claim support.** Add a bounded local review pass for entailment, negation, attributable third-party opinions, causal mechanisms, duplicate arguments and questions already answered by evidence. Agreement between local model passes is not independent verification; difficult cases must retain uncertainty or be withheld.
3. **Improve primary-source retrieval.** Read relevant SEC earnings exhibits and authorised issuer/media originals, identify product/subsidiary links with provenance and retain contradictions. General web research and semantic retrieval remain pending.
4. **Build the 3–6-month decision framework.** Distinguish confirmed/estimated catalyst dates, include events between the analysis date and target dates, and construct conditional bear/base/bull cases with justified inputs, risks and invalidation. Do not turn an article opinion or an estimated date into a certified forecast.

The current update improves the known errors; it does not certify investment quality, price predictions, exhaustive coverage or universal market support. It uses the existing local model and keeps paid AI independently disabled by default.

## Windows installation

The updated `scripts/update_local_ai.py` verifies a pinned eight-file manifest, backs up code, rebuilds the financial-report interface and reanalyzes saved sources. Stop Stock Analyser with Ctrl+C first and leave LM Studio running. No dependency changes or credential re-entry are needed for an existing installation. The updater checks the app ports before proceeding and starts the app after reanalysis. A failed build restores the previous source/build; `.env`, models and original research records are preserved. `--install-only` and `--no-start` support controlled checks.
