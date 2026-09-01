# Offline AI Fallback

A personal AI assistant that runs locally on your PC using [Ollama](https://ollama.com), and automatically falls back to that local model whenever an online AI service or internet connection is unavailable. Built for reliability and privacy — your data never has to leave your machine.

## Why this exists

Online AI tools are great until your internet drops. This project keeps you working by silently switching to a local, fully offline model — no manual switching, no lost work.

## Features

- **Automatic fallback** — tries an online AI first (if configured), falls back to a local Ollama model automatically if offline or if the online request fails
- **Prompt length safety limit** — rejects overly long messages with a clear notice instead of risking a timeout on CPU-only hardware
- **Privacy-first** — local models run entirely on-device; nothing is sent anywhere unless an online AI is explicitly configured
- **Built-in testing agent** — a dedicated tool (`testing_agent.py`) that runs edge-case scenarios against the fallback logic, catches crashes with full details, and tracks CPU/RAM usage during each test

## Requirements

- Windows 10/11 (cross-platform support planned)
- Python 3.9+
- [Ollama](https://ollama.com) installed, with a model pulled (e.g. `llama3.2:3b`)

## Installation

1. Clone this repository:
   ```
   git clone <your-repo-url>
   cd offline-ai
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Install [Ollama](https://ollama.com) and pull a model:
   ```
   ollama pull llama3.2:3b
   ```

## Usage

Run the assistant directly from the command line:

```
python ai_fallback.py
```

Type a message and press Enter. Type `exit` to quit.

To connect an online AI service instead of relying on local-only mode, edit the `API_URL` and `API_KEY` variables in `ai_fallback.py`'s `__main__` section.

## Running the tests

A dedicated testing agent checks the fallback logic for bugs and crashes before you rely on it:

```
python testing_agent.py
```

This runs a set of edge-case scenarios (empty input, very long input, special characters, rapid repeated requests, simulated provider failure, and some more senerios), logs CPU/RAM usage during each test, and saves a full report to `test_report.json` with proper timing and date.

## Project structure

```
offline-ai/
├── ai_fallback.py       # Core logic: online/local AI routing
├── testing_agent.py     # Automated tests + crash/performance reporting
├── requirements.txt     # Python dependencies
└── README.md
```

## How it works

1. A message comes in.
2. If it's over the length limit, a friendly notice is returned instead of processing it.
3. If an online AI is configured and internet is available, try that first.
4. If the online request fails, or there's no internet, fall back to the local Ollama model.
5. Return the answer.

See `ai_fallback.py` for the full implementation.

## Roadmap

- [ ] Package as a standalone `.exe` for easy installation
- [ ] Extend to Mac/Linux
- [ ] Add a simple GUI chat window
- [ ] Automated testing on every code change (CI)
