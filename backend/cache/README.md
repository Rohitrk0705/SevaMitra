# backend/cache

Pre-recorded Featherless responses for demo reliability — lets a demo run
replay known-good LLM outputs instead of depending on a live API call
mid-presentation.

## How it works

`backend/llm.py`'s `chat()` and `chat_json()` both check here first when
`USE_CACHED_LLM=true` is set. The cache key is a SHA-256 hash of the exact
messages sent (plus which of the two functions was called, so identical
messages sent through `chat()` and `chat_json()` don't collide). On a
cache **hit**, the recorded response is returned and no network call is
made. On a cache **miss**, the live Featherless call still happens as
normal, and its result is written to `<hash>.json` here — so cached
responses get recorded simply by running a flow once with the env var
set.

## Re-recording cached responses

1. Set `USE_CACHED_LLM=true` in `.env` (or export it directly).
2. Run the flow(s) you want cached end-to-end (e.g.
   `python -m backend.graph.run "..."`, or the relevant agent directly).
   Every LLM call along the way that isn't already cached will hit
   Featherless live once and get written here.
3. Review the new `*.json` files before committing — each one is the
   verbatim parsed/plain response for one exact set of input messages.
   If a prompt template changes, its cache key changes too, so stale
   entries just stop being hit rather than silently going wrong; they can
   be deleted.

## What's committed here

Only `.gitkeep` and this README as of Rung 9 — the caching
*infrastructure* is wired up, but no real recorded responses are
committed yet. That's a deliberate manual "record a demo run" step done
once the Discovery/Validator/Filler flows are stable, not part of this
rung. `*.json` files in this directory are gitignored in the meantime so
a local `USE_CACHED_LLM=true` run doesn't accidentally get committed.
