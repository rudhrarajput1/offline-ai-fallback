"""
AI Fallback System
-------------------
Automatically switches between an online AI service and your local Ollama
model depending on internet connectivity.

Requires: pip install requests --break-system-packages
Requires: Ollama installed and running locally (ollama serve, then ollama run <model>)

--- Using a different online AI provider ---
Three provider adapters are built in: "gemini", "openai", and "generic".
To switch providers, just change ONLINE_PROVIDER near the bottom of this file
and set the matching environment variable for your API key. To add a provider
that isn't listed, add one function to PROVIDERS below following the same
pattern (build the request, parse the response) — nothing else needs to change.

Never hardcode a real API key in this file. Always read it from an
environment variable so it's safe to commit/share this code publicly.
"""

import concurrent.futures
import os
import socket

import requests


def is_online(timeout=2):
    """Quick check: can we reach the internet right now?"""
    try:
        s = socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        s.close()
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Online provider adapters
#
# Each adapter is a function: (prompt, api_url, api_key) -> response_text
# Add a new one here to support a different AI service; nothing else in the
# file needs to change.
# ---------------------------------------------------------------------------

def _call_gemini(prompt, api_url, api_key):
    headers = {"Content-Type": "application/json"}
    params = {"key": api_key}
    body = {"contents": [{"parts": [{"text": prompt}]}]}

    response = requests.post(api_url, headers=headers, params=params, json=body, timeout=10)
    response.raise_for_status()
    data = response.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        return ""


def _call_openai(prompt, api_url, api_key):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    body = {
        "model": "gpt-4o-mini",  # change to whichever model you want
        "messages": [{"role": "user", "content": prompt}],
    }

    response = requests.post(api_url, headers=headers, json=body, timeout=10)
    response.raise_for_status()
    data = response.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        return ""


def _call_generic(prompt, api_url, api_key):
    """
    Fallback adapter for a simple custom/self-hosted API that accepts
    {"prompt": "..."} with a Bearer token and returns {"response": "..."}.
    Adjust this if your custom API's shape differs.
    """
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = requests.post(api_url, headers=headers, json={"prompt": prompt}, timeout=10)
    response.raise_for_status()
    return response.json().get("response", "")


PROVIDERS = {
    "gemini": _call_gemini,
    "openai": _call_openai,
    "generic": _call_generic,
}


def ask_online_ai(prompt, api_url, api_key, provider="gemini"):
    """Send the prompt to whichever online AI provider is configured."""
    if not api_key:
        raise ValueError("No API key provided for online AI")
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider '{provider}'. Options: {list(PROVIDERS)}")

    return PROVIDERS[provider](prompt, api_url, api_key)


def ask_local_ai(prompt, model="llama3:latest"):
    """Send the prompt to your local Ollama model instead."""
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=300,
    )
    response.raise_for_status()
    return response.json().get("response", "")


def ask_ai(prompt, api_url=None, api_key=None, provider="gemini", model="llama3:latest"):
    """
    Backwards-compatible helper: single-provider call. Tries online first when
    api_url and api_key are provided and we're online, otherwise uses local Ollama.
    """
    MAX_PROMPT_CHARS = 2000

    if len(prompt) > MAX_PROMPT_CHARS:
        return (f"[notice] Your message is too long ({len(prompt)} characters). "
                f"Please shorten it to under {MAX_PROMPT_CHARS} characters and try again.")

    if api_url and api_key and is_online():
        try:
            print(f"[status] Online — using {provider}")
            return ask_online_ai(prompt, api_url, api_key, provider)
        except requests.RequestException:
            print("[status] Online AI failed to respond — falling back to local AI")
            return ask_local_ai(prompt, model)
    else:
        print("[status] Offline (or no API key set) — using local Ollama model")
        return ask_local_ai(prompt, model)


def ask_ai_race(prompt, api_url=None, api_key=None, provider="gemini", model="llama3:latest"):
    """
    Race both providers in real-time and return the first successful result.

    Behavior:
    - If api_url/api_key aren't both set, or we're offline, calls local only.
    - Otherwise starts local immediately and online concurrently; returns
      whichever completes successfully first.
    - If one provider errors, waits for the other. If both fail, raises RuntimeError.
    """
    MAX_PROMPT_CHARS = 2000
    if len(prompt) > MAX_PROMPT_CHARS:
        return (f"[notice] Your message is too long ({len(prompt)} characters). "
                f"Please shorten it to under {MAX_PROMPT_CHARS} characters and try again.")

    if not api_url or not api_key or not is_online():
        print("[race] Offline or no API key set — using local Ollama model")
        return ask_local_ai(prompt, model)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        future_to_provider = {
            ex.submit(ask_local_ai, prompt, model): "local",
            ex.submit(ask_online_ai, prompt, api_url, api_key, provider): "online",
        }

        first_exception = None
        for fut in concurrent.futures.as_completed(future_to_provider):
            provider_name = future_to_provider[fut]
            try:
                result = fut.result()
                if result is not None:
                    print(f"[race] {provider_name} responded first")
                    for other in future_to_provider:
                        if other is not fut and not other.done():
                            try:
                                other.cancel()
                            except Exception:
                                pass
                    return result
            except Exception as e:
                print(f"[race] {provider_name} failed: {e}")
                if first_exception is None:
                    first_exception = e

        raise RuntimeError("Both AI providers failed to return a response") from first_exception


if __name__ == "__main__":
    # --- Choose your online provider here ---
    # Options: "gemini", "openai", "generic" (or your own added to PROVIDERS above)
    ONLINE_PROVIDER = "gemini"

    PROVIDER_CONFIG = {
        "gemini": {
            "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent",
            "key_env": "GEMINI_API_KEY",
        },
        "openai": {
            "url": "https://api.openai.com/v1/chat/completions",
            "key_env": "OPENAI_API_KEY",
        },
        "generic": {
            "url": os.environ.get("CUSTOM_AI_URL", ""),
            "key_env": "CUSTOM_AI_API_KEY",
        },
    }

    _cfg = PROVIDER_CONFIG[ONLINE_PROVIDER]
    API_URL = _cfg["url"]
    API_KEY = os.environ.get(_cfg["key_env"])  # never hardcode a real key here

    print("AI Fallback demo. Type 'exit' to quit.\n")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break

        try:
            answer = ask_ai_race(user_input, api_url=API_URL, api_key=API_KEY,
                                  provider=ONLINE_PROVIDER, model="llama3:latest")
        except Exception as exc:
            answer = f"[error] {exc}"
        print(f"AI: {answer}\n")
