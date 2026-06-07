# What to do if the LLM is not responding?

**The batch is not being processed. The journal shows connection errors to the language model.**

## Direct answer

The language model server is not reachable: it is off, not started, or the address is set incorrectly.

## Step-by-step solution

1. Open Settings → LLM.
2. Click "Test connection" (or the 🔌 button in the navigation bar).
3. If the test returns an error — make sure your model server is running.
4. Check the `base_url` field: default is `http://localhost:1234/v1`. If your server listens on a different port — update it.
5. Make sure `model_id` matches the model loaded on the server.
6. Click "Save" after any changes and repeat the test.

If the test passes, the pipeline will resume automatically on the next processing attempt. If the batch is stuck — click Pause, then Resume.

## If the server is reachable but errors continue

- Check the Journal: filter by level ERROR → find the entry with the error code.
- Increase `request_timeout` (default 600 seconds) — some models on slow hardware respond more slowly.
- Enable `debug_dump_llm_io` under Settings → Logging — raw requests and responses will be written to files for diagnostics.

## References

For LLM parameter details, see [LLM Settings](ref_llm_settings.md).
