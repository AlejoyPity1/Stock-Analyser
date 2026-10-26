# Local Qwen connection

Use **LM Studio on the same Windows PC as Stock Analyser**. Confirmed model ID reported by the user's `/v1/models` request: **`qwen/qwen3.5-9b`**. `text-embedding-nomic-embed-text-v1.5` is an embedding model, not the synthesis model.

The user completed the synthetic structured-output/quotation check on Windows, installed and built the app, and opened the running interface. Screenshots identify the actual downloaded file as **Qwen3.5-9B-Q4_K_M.gguf**, although Q6_K was originally recommended. The first real AAPL research collected sources but its synthesis was rejected (615 completion tokens, zero reasoning tokens); its exact validation failure still needs diagnosis. GPU acceleration, speed and financial quality remain unverified. See [the Windows evidence record](LOCAL_WINDOWS_CHECK.json).

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
- Uses LM Studio's `/v1/chat/completions` with a JSON schema and the exact model ID. No embedding model substitution, tools, MCPs, recursive agents or valuation changes.
- Serializes generation for a single GPU. Quick defaults to at most 6 evidence batches; Deep to 12. Calls have a configured timeout, bounded responses and no automatic retries/provider switching.
- Reserves output/schema/template space within the configured context using a conservative UTF-8 byte budget. This is intentionally conservative, not an exact Qwen tokenizer measurement. LM Studio's actual loaded context must be at least the configured value.
- Selects up to two exact contiguous keyword windows per readable source. Each source gets a first window before any second windows. This is deterministic excerpt selection, **not semantic retrieval or exhaustive reading**. Inaccessible/unread content is excluded.
- Validates each claim and each side of a contradiction against the excerpts actually sent in that batch. A quote elsewhere in a full retrieved document does not pass. Invalid JSON, truncated completion, tool calls or unmatched quotes reject the entire synthesis.
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

The user-reported Windows checks, controlled transport tests and real-source synthesis validation are distinct evidence. The synthetic check passed; real-source synthesis is still under diagnosis.
