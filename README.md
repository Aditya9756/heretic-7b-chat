# Heretic 7B Chat (GitHub Actions)

On-demand fast chat sessions for the Heretic-modified Qwen2.5-7B-Instruct
(Trial 6 LoRA). Runs on GitHub's free standard runner (4 vCPU / 16 GB),
much faster than the small VM the 24/7 server lives on.

## Start a session

1. Open the **Actions** tab -> **7B Chat Server** -> **Run workflow**.
2. Wait ~5-8 minutes (model download + server start).
3. Open the running job's log and search for `CHAT-LINK:` — that is the
   public chat URL. Append `?key=<your key>` to it (the key is stored as
   the repo secret `CHAT_KEY` and is never printed in the log).
4. The session runs up to ~5.5 hours, then stops by itself. Start a new
   run whenever you want to chat again.

## What runs

- Base model: Qwen2.5-7B-Instruct Q4_K_M GGUF (downloaded from Hugging Face
  at session start, 2 split parts, ~4.7 GB).
- Adapter: Trial 6 Heretic LoRA (`trial6-lora.gguf`, 166 MB) from this
  repo's `v1.0` release.
- Engine: llama.cpp `llama-server` (prebuilt CPU binary) + a tiny Python
  chat proxy (`chat_proxy_llama.py`) + a pinggy tunnel for the public link.

## Notes

- This repo is public so Actions minutes are free and unlimited. The chat
  key stays a secret; never commit it.
- Do not chain runs to fake 24/7 — GitHub Actions is for CI/CD, and
  abusing it as an always-on server risks the account. The VM server is
  the 24/7 fallback.
