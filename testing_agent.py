"""
Testing Agent
-------------
Runs a set of test scenarios against your AI fallback system,
catches crashes with full details, and logs PC performance
(CPU/RAM) during each test so you can spot what's slow or broken.

Requires: pip install psutil requests --break-system-packages
Requires: ai_fallback.py in the same folder
Requires: Ollama running locally with a model pulled
"""

import time
import traceback
import json
from datetime import datetime
import psutil
from ai_fallback import ask_ai, is_online


REPORT_FILE = "test_report.json"


def get_system_status():
    """Snapshot of current CPU and RAM usage."""
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "ram_percent": psutil.virtual_memory().percent,
        "ram_used_gb": round(psutil.virtual_memory().used / (1024**3), 2),
    }


def run_test(name, func):
    # Runs a single test, catches any crash, records timing + stats.
    print(f"\n[TEST] {name}")
    before_stats = get_system_status()
    start = time.time()
    result = {
        "name": name,
        "timestamp": datetime.now().isoformat(),
        "status": "pass",
        "error": None,
        "duration_seconds": None,
        "stats_before": before_stats,
        "stats_after": None,
    }

    try:
        func()
    except Exception as e:
        result["status"] = "FAIL"
        result["error"] = {
            "type": type(e).__name__,
            "message": str(e),
            "traceback": traceback.format_exc(),
        }
        print(f"  -> CRASH: {type(e).__name__}: {e}")
    else:
        print("  -> passed")

    result["duration_seconds"] = round(time.time() - start, 2)
    result["stats_after"] = get_system_status()
    return result



# Test scenarios — add more here as you think of edge cases


def test_basic_prompt():
    response = ask_ai("Say hello in one short sentence.")              # for empty responses, we want to catch that as a failure
    assert response, "Empty response received"


def test_empty_prompt():
    response = ask_ai("")                                              # Should not crash even with empty input
    assert response is not None


def test_long_prompt():
    long_text = "Explain the water cycle. " * 200                      # deliberately long , fail the test if it exceed the max. limit 
    response = ask_ai(long_text)
    assert response is not None


def test_special_characters():
    response = ask_ai("What about symbols like é, 中文, emojis 🚀, and \n newlines?")
    assert response is not None                                        # test with the special characters and unicode , special cases like emojis, newslines, doifferent lanuagese etc.


def test_connectivity_check():
    status = is_online()
    assert isinstance(status, bool)


def test_repeated_rapid_requests():
    for _ in range(4):
        response = ask_ai("Quick test.")                               # repeated rpaid tests , run "quick test" or anything else multiple times like there is 4 so four times in a row one after another without any breaks to check if the system can handle rapid requests without crashing or failing
        assert response is not None

def test_provider_failure():
    response = ask_ai("Simulate failure test.", api_url="http://invalid.url")  # handle the cases where the provider fails, it make sure that the system can handle the provider failure gracefully without crashing or throwing unhandled exceptions 
    assert response is not None

# Runner


def main():
    tests = [
        ("Basic prompt", test_basic_prompt),
        ("Empty prompt", test_empty_prompt),
        ("Very long prompt", test_long_prompt),
        ("Special characters / unicode", test_special_characters),
        ("Connectivity check", test_connectivity_check),
        ("Repeated rapid requests", test_repeated_rapid_requests),
        ("Simulated provider failure", lambda: ask_ai("Simulate failure test.", api_url="http://invalid.url")),
    ]

    results = []
    for name, func in tests:
        results.append(run_test(name, func))

    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "FAIL")

    summary = {
        "run_at": datetime.now().isoformat(),
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "results": results,
    }

    with open(REPORT_FILE, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*40}")
    print(f"Done: {passed} passed, {failed} failed")
    print(f"Full report saved to {REPORT_FILE}")
    print(f"{'='*40}")

    if failed:
        print("\nFailed tests:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"  - {r['name']}: {r['error']['type']}: {r['error']['message']}")


if __name__ == "__main__":
    main()
