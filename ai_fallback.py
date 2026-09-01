"""
AI Fallback System
------------------- 
Automatically switches between an online AI service and your local
Ollama model depending on internet connectivity.

Requires: pip install requests --break-system-packages
Requires: Ollama installed and running locally (ollama run <model>)
"""

import concurrent.futures
import socket

import requests

def is_online(timeout=2):
    # Quick check: can we reach the internet right now?

    # Uses socket.create_connection and ensures the socket is closed.
    
    try:
        # create_connection handles DNS + connect; make sure to close the socket
        s = socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        s.close()
        return True
    except OSError:
        return False


def ask_online_ai(prompt, api_url, api_key=None):
    # Send the prompt to your online AI service. Adjust this to match
    # whichever online AI API you're actually using.
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = requests.post(
        api_url,
        headers=headers,
        json={"prompt": prompt},
        timeout=10,
    )
    response.raise_for_status()
    return response.json().get("response", "")


def _ask_online_ai_impl(prompt, api_url, api_key=None):
    # Replacement implementation that correctly includes the api_key in headers.

    # This wrapper exists to avoid editing the original ask_online_ai function body directly.
    # The module-level name `ask_online_ai` will be reassigned to point to this implementation.
    
    headers = {"Content-Type": "application/json"}
    if api_key:
        # include api_key using a common Bearer scheme; adjust if your API expects a different format
        headers["Authorization"] = f"Bearer {api_key}"

    response = requests.post(
        api_url,
        headers=headers,
        json={"prompt": prompt},
        timeout=10,
    )
    response.raise_for_status()
    return response.json().get("response", "")

# Reassign the public API name to the implementation above so all callers use it.
ask_online_ai = _ask_online_ai_impl


def ask_local_ai(prompt, model="llama3.2:3b"):
    # Send the prompt to your local Ollama model instead.
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=60,
    )
    response.raise_for_status()
    return response.json().get("response", "")


def ask_ai(prompt, api_url=None, api_key=None, model="llama3.2:3b"):
    
    # Backwards-compatible helper: single-provider call. Tries online first when
    # api_url is provided and we're online, otherwise uses local Ollama.
    
    MAX_PROMPT_CHARS = 2000  # keeps responses fast and predictable on CPU-only hardware

    if len(prompt) > MAX_PROMPT_CHARS:
        return (f"[notice] Your message is too long ({len(prompt)} characters). "
                f"Please shorten it to under {MAX_PROMPT_CHARS} characters and try again.")

    if api_url and is_online():
        try:
            print("[status] Online — using cloud AI")
            return ask_online_ai(prompt, api_url, api_key)
        except requests.RequestException:
            print("[status] Online AI failed to respond — falling back to local AI")
            return ask_local_ai(prompt, model)
    else:
        print("[status] Offline — using local Ollama model")
        return ask_local_ai(prompt, model)


def ask_ai_race(prompt, api_url=None, api_key=None, model="llama3.2:3b", prefer_local=False):
    """
    Race both providers in real-time and return the first successful result.

    Behavior:
    - If api_url is not provided or we're offline, calls local only.
    - Otherwise starts local immediately and online concurrently; returns
      whichever completes successfully first.
    - If one provider errors, waits for the other. If both fail, raises RuntimeError.

    Note: requests can't be forcefully cancelled; the other call is left to finish
    in the background but its result is ignored once a winner is chosen.
    """
    # Quick length check
    MAX_PROMPT_CHARS = 2000
    if len(prompt) > MAX_PROMPT_CHARS:
        return (f"[notice] Your message is too long ({len(prompt)} characters). "
                f"Please shorten it to under {MAX_PROMPT_CHARS} characters and try again.")

    # If no online endpoint configured or offline, use local only
    if not api_url or not is_online():
        print("[race] Offline or no api_url — using local Ollama model")
        return ask_local_ai(prompt, model)

    # Start both providers in parallel and take the first successful response
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        future_to_provider = {
            ex.submit(ask_local_ai, prompt, model): "local",
            ex.submit(ask_online_ai, prompt, api_url, api_key): "online",
        }

        first_exception = None
        try:
            for fut in concurrent.futures.as_completed(future_to_provider):
                provider = future_to_provider[fut]
                try:
                    result = fut.result()
                    if result is not None:
                        print(f"[race] {provider} responded first")
                                                                     # attempt to cancel other pending futures (best-effort)
                        for other in future_to_provider:
                            if other is not fut and not other.done():
                                try:
                                    other.cancel()
                                except Exception:
                                    pass
                        return result
                except Exception as e:
                                                                     # record first exception and continue waiting for the other
                    print(f"[race] {provider} failed: {e}")
                    if first_exception is None:
                        first_exception = e
                                                                     # If loop finishes with no successful result
            raise RuntimeError("Both AI providers failed to return a response") from first_exception
        finally:
                                                                     # best-effort: let ThreadPoolExecutor clean up
            pass


if __name__ == "__main__":
    API_URL = None                                                   # e.g. "https://api.example.com/generate"
    API_KEY = None

    print("AI Fallback demo. Type 'exit' to quit.\n")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break

        try:
            answer = ask_ai_race(user_input, api_url=API_URL, api_key=API_KEY, model="llama3.2:3b")
        except Exception as exc:
            answer = f"[error] {exc}"
        print(f"AI: {answer}\n")
