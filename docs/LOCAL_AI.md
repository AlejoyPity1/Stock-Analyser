# Local Qwen connection

Use **LM Studio on the same Windows PC as Stock Analyser**. Confirmed model ID reported by the user's `/v1/models` request: **`qwen/qwen3.5-9b`**. `text-embedding-nomic-embed-text-v1.5` is an embedding model, not the synthesis model.

The user completed Windows installation/build/startup and the original synthetic check with **Qwen3.5-9B-Q4_K_M.gguf**. A saved-source diagnostic identified shortened quotations containing `...` and altered punctuation in real AAPL output. After installing the evidence-ID correction, the user completed **all 6 planned local batches**, producing **16 claims referencing 14 sources**, with zero paid API calls and no new source retrieval. A new record was created and the original preserved; the user also restarted the app and reported Ready. GPU acceleration, speed, claim semantics and financial quality remain unverified. See [the Windows evidence record](LOCAL_WINDOWS_CHECK.json).

## Windows setup

1. Install the repository dependencies using `scripts/install.ps1` after obtaining the current application code. Existing GitHub screenshot-only branches do **not** contain the application.
2. Copy `.env.example` to `.env` at the repository root. Preserve any existing local credentials. Configure SEC contact identification and your market-provider keys locally; the cloud environment's injected credentials do not automatically transfer to Windows.
3. Set the following in that file:

```dotenv
AI_PROVIDER=local
LOCAL_AI_BASE_URL=http://127.0.0.1:1234/v1
LOCAL_AI_MODEL=qwen/qwen3.5-9b
LOCAL_AI_CONTEXT_TOKENS=8192
LOCAL_AI_MAX_OUTPUT_TOKENS=1200
PAID_AI_ENABLED=false
```

4. In LM Studio, load **one** downloaded Qwen3.5-9B GGUF with an 8192-token context and GPU offload suitable for the RX 9060 XT. The user's installed file is Q4_K_M; a quantization change is not required to run this connector. Start its server on port 1234. LAN serving and CORS can remain off. Per-request MCPs are not used. If authentication is enabled, put the local token in `LOCAL_AI_API_KEY`; never paste that token into chat or the browser.
5. Start the application with `scripts/start.ps1`. In Settings, **Check local model** verifies the exact model ID is listed. This check deliberately does not claim successful inference or GPU acceleration.
6. Run the structured-output check in PowerShell from the repository:

```powershell
.\.venv\Scripts\python.exe scripts/verify_local_ai.py
```

This sends synthetic evidence through the same local connector and validates response completion, the schema and quotation matching. It saves `local-ai-check.json`, ignored by Git. It does not persist a synthetic company in the database. A successful result is not a financial-quality benchmark. Inspect the generated claims and LM Studio GPU/performance display as well.

7. Research has **Use AI for evidence analysis** selected initially when the local provider is enabled. Start Quick or Deep for the chosen ticker/horizon. English claims, bullish/bearish arguments, questions, coverage and omissions are saved with the job and exported in JSON/PDF. The user can turn AI off; refreshing Settings does not override that choice.

The cloud workspace cannot connect to the Windows PC's localhost. This version accepts only literal loopback endpoints (or `localhost`, normalized without DNS). Running the backend remotely would need a separately designed private connection; opening the model server to the internet is unnecessary for this setup.

## What the connector does

- Explicit `AI_PROVIDER=disabled|local|openai`; the code default is disabled and the Windows example selects local. Local calls never fall back to OpenAI. Paid mode additionally requires `PAID_AI_ENABLED=true`, credentials and verified pricing.
- Uses LM Studio's `/v1/chat/completions` with a JSON schema and the exact model ID. The local schema restricts evidence IDs to those in the current batch. No embedding model substitution, tools, MCPs, recursive agents or valuation changes.
- Serializes generation for a single GPU. Quick defaults to at most 6 evidence batches; Deep to 12. Calls have a configured timeout, bounded responses and no automatic retries/provider switching.
- Reserves output/schema/template space within the configured context using a conservative UTF-8 byte budget. This is intentionally conservative, not an exact Qwen tokenizer measurement. LM Studio's actual loaded context must be at least the configured value.
- Selects up to two exact contiguous keyword windows of at most 900 UTF-8 bytes per readable source. Each source gets a first window before any second windows. This is deterministic excerpt selection, **not semantic retrieval or exhaustive reading**. Inaccessible/unread content and windows too short for a valid quotation are excluded and source omissions are recorded.
- The local model returns claim text, type, mechanism and an evidence ID, rather than typing a quotation. The server resolves that ID to the exact source ID and entire supplied window, preserving whitespace and Unicode punctuation. Source-window offsets/hashes and selected IDs are audited. Unknown IDs, references to another batch, model-written quote overrides, invalid JSON, truncation and tool calls reject the entire synthesis. Contradictions additionally require distinct original sources; two windows from one filing do not count as two sources. The shared report/paid-provider schema remains unchanged.
- Copying an exact window establishes text provenance by construction, **not semantic support**. The user must still review whether that window supports the claim; no interpretation or forecast is certified by a valid citation.
- Merges checked batch claims into bounded output without inventing an uncited final narrative. Cross-source conflicts can only be detected within the same batch; global contradiction analysis remains pending.
- Keeps source-window offsets/hashes, included/omitted source IDs, truncation, request hashes, usage, model/provider and zero API billing. Zero API billing excludes electricity and hardware costs.
- A matching quotation does not certify the interpretation, prediction or investment thesis. Semantic deduplication, original-media full-text retrieval, richer retrieval/reranking and quality evaluation remain future work.

## Troubleshooting

- **Thinking with LM Studio 0.4.26:** select the intended model, open **Inference > Custom Fields > Enable Thinking**, and turn it off for the initial 1200-token check. The separate **Reasoning** section contains a budget control. In **Model Server**, **Eject** unloads each model row. Loading repeatedly can create IDs such as `qwen/qwen3.5-9b:2`; unload duplicates and load one copy, then confirm thinking is off on the exact configured instance.
- **Cannot reach LM Studio:** start its server on the same PC; verify port 1234.
- **Model missing:** use the exact ID `qwen/qwen3.5-9b`, not the GGUF filename or the embedding ID.
- **401:** set the optional local token when LM Studio requires authentication.
- **Rejected/incomplete output:** the check now prints the rejection code, reason, usage and safe response diagnostics. `local_ai_output_truncated` means the model reached its output limit; inspect `reasoning_tokens` and `content_characters`. Configure thinking for the **server model** if reasoning consumes the output budget; a chat-only toggle may not change API behavior. `local_ai_invalid_json`, `local_ai_invalid_synthesis` and `local_ai_unmatched_quote` identify different failures and must not be treated as token-limit errors. Output is rejected rather than stripping thought text or fabricating a result. Increase the output allowance only with sufficient loaded context. The native REST chat API documents a `reasoning` option, but that is a different endpoint from this connector's OpenAI-compatible `/v1/chat/completions`; do not assume its parameters apply here.
- **Slow/timeout:** check that LM Studio uses the RX 9060 XT, reduce context/output as appropriate and verify driver/runtime support. No tokens-per-second guarantee has been measured on the user's GPU.

For a rejected saved research run, execute `scripts/diagnose_local_ai.py` on the Windows PC. It repeats **one** first-batch inference using the saved source text, original horizon and current local settings. It prints safe schema errors or explicitly unverified quotation mismatches and records whether the request hash matches the original first batch. It never retrieves new public sources, changes the research record, publishes a synthesis or relaxes literal quote validation. It is compatible with the initial application ZIP and can be installed as a single new script without restarting the app. Optional `--symbol` or `--record` selects a particular saved run; the default uses the latest research. The ignored `local-ai-diagnostic.json` contains the diagnostic. A fresh replay can differ from the original response and does not validate later batches.

The user-reported Windows checks and controlled transport tests are distinct evidence. Both the original synthetic check and the corrected full saved-source run passed their structured-output/citation checks. Semantic support and financial quality still need review.

## Updating the original Windows ZIP

`scripts/update_local_ai.py` installs exactly three Python files from a pinned repository commit after checking every SHA-256 and compiling every download. It backs up existing code under `.local-ai-backups/` and rolls back replaced code if installation fails. It preserves `.env`, model files, dependencies and existing records. No frontend rebuild is required.

By default it then runs `scripts/reanalyze_local_ai.py` in a fresh process. Reanalysis uses all planned local batches from the latest saved research, with its original source snapshot and investment horizon. It downloads no new sources and uses no paid provider. Only a completed synthesis with at least one checked claim creates a **new** research record; the original remains unchanged. The full result is saved to `local-ai-reanalysis.json`, and the summary reports the new record ID. Optional `--symbol`/`--record` on the reanalysis script selects another saved run.

The app can remain open during installation and reanalysis. Its existing backend process loads the correction after its next restart; future research from the UI requires that restart. The normalized report remains compatible with the original frontend/report exporter.

Controlled tests verify Unicode preservation, batch/ID restrictions, distinct-source conflicts, full prompt/schema/output budgets, preservation of credentials and original records, and rollback. A handoff test applies the update to the original ZIP's source and completes four controlled local batches, saving a new record without changing the original. This is not a real-Qwen or Windows execution of the replacement.
