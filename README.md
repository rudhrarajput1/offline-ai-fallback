# Offline AI Fallback

A personal AI assistant that automatically switches between an
online model (Google Gemini) and a local Ollama model, so it keeps
working when the internet doesn't.

> **Why:** I wanted an AI assistant that doesn't just stop working
> the moment Wi-Fi drops — reliability over relying on one provider.

## Architecture

```
User request
     │
     ▼
Connectivity check
     │
 ┌───┴────┐
 online?  offline?
 │          │
 ▼          ▼
Gemini    Ollama (local model)
   API
```

## Tech stack

`Python` · `Google Gemini API` · `Ollama`

## Why these design choices

- **Gemini over the Claude API**: switched early on for the online
  component based on cost/access tradeoffs for this personal project.
- **Ollama for the offline path**: runs fully locally, no internet
  required once a model is pulled — keeps the assistant usable with
  zero connectivity.
- **Reliability prioritized over novelty**: favored a simple, working
  fallback switch over more ambitious but less stable approaches.

## Limitations

- Currently Windows-only; cross-platform support is a future goal
- Personal/single-user only by design — no multi-user or auth layer
- No voice interface yet (text only, for now)
- Local model quality is lower than the online model for complex,
  multi-step reasoning

## Setup

```bash
pip install -r requirements.txt
```

- Install [Ollama](https://ollama.com) and pull a model, e.g.
  `ollama pull llama3`
- Set `GEMINI_API_KEY` as an environment variable for the online path

## License

MIT — see [LICENSE](LICENSE).

## Status

Actively developed. A focused testing/bug-finding agent exists
alongside this project to catch crashes and track performance during
development. Planned: packaging as a standalone installer, and voice
input/output.
