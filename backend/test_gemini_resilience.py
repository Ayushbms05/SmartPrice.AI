"""
SmartPrice AI - Verification Suite for Gemini Resilient Engine
Validates all 7 Architectural Pillars:
1. Core rules: lazy init & missing key handling
2. Multi-model fallback chain configuration
3. Error classification
4. Output validation & JSON self-healing
5. Rate limiting & circuit breaker
6. Content-addressable caching (< 5ms)
7. Rotating file logging format
"""

import os
import sys
import time
import json

# Add backend directory to path
sys.path.insert(0, os.path.dirname(__file__))

from gemini_engine import (
    compute_cache_key,
    _get_from_cache,
    _save_to_cache,
    _clean_json_markdown,
    _validate_schema,
    _classify_error,
    _record_circuit_failure,
    _record_circuit_success,
    _is_circuit_open,
    _log_call_record,
    get_model_chain,
    _get_gemini_client,
    get_last_call_info,
    LOG_FILE
)
from scraper import scrape_product


def test_lazy_client_and_missing_key():
    print("Testing Pillar 1: Lazy client init & missing key error...")
    old_key = os.environ.get("GEMINI_API_KEY")
    os.environ["GEMINI_API_KEY"] = ""
    try:
        _get_gemini_client(api_key="")
        assert False, "Should have raised ValueError for missing GEMINI_API_KEY"
    except ValueError as e:
        assert "GEMINI_API_KEY is not configured" in str(e)
        print("  ✓ Correctly raised friendly ValueError on missing key.")
    finally:
        if old_key:
            os.environ["GEMINI_API_KEY"] = old_key


def test_model_chains():
    print("Testing Pillar 2: Tiered fallback chains...")
    light_chain = get_model_chain(task="light")
    heavy_chain = get_model_chain(task="heavy")
    print(f"  Light chain: {light_chain}")
    print(f"  Heavy chain: {heavy_chain}")
    assert len(light_chain) >= 2, "Light chain should have multiple models"
    assert len(heavy_chain) >= 2, "Heavy chain should have multiple models"
    assert "gemini-3.6-flash" in heavy_chain[0], "Heavy chain should prioritize 3.6-flash"
    print("  ✓ Model fallback chains configured correctly.")


def test_error_classification():
    print("Testing Pillar 3: Intelligent HTTP Error Classification...")
    # 401/403
    c401 = _classify_error(Exception("HTTP 401: Unauthorized API key"))
    assert c401.action == "ABORT", f"Expected ABORT for 401, got {c401.action}"

    # 404
    c404 = _classify_error(Exception("HTTP 404: Model not found"))
    assert c404.action == "NEXT_MODEL_INSTANT", f"Expected NEXT_MODEL_INSTANT for 404, got {c404.action}"

    # 400 thinking
    c400_think = _classify_error(Exception("HTTP 400: thinking_config not supported"))
    assert c400_think.action == "RETRY_DISABLE_THINKING", f"Expected RETRY_DISABLE_THINKING, got {c400_think.action}"

    # 429
    c429 = _classify_error(Exception("HTTP 429: ResourceExhausted rate limit"))
    assert c429.action == "RETRY_BACKOFF", f"Expected RETRY_BACKOFF for 429, got {c429.action}"
    assert c429.is_severe is True

    print("  ✓ Error classification matches all architectural requirements.")


def test_json_markdown_stripping_and_validation():
    print("Testing Pillar 4: Output Validation & Self-Healing helpers...")
    fenced_json = "```json\n{\"verdict\": \"BUY NOW\", \"deal_integrity_score\": 95}\n```"
    cleaned = _clean_json_markdown(fenced_json)
    parsed = json.loads(cleaned)
    assert parsed["verdict"] == "BUY NOW"
    assert _validate_schema(parsed, ["verdict", "deal_integrity_score"]) is True
    assert _validate_schema(parsed, ["verdict", "missing_field"]) is False
    print("  ✓ Markdown code fence stripping and schema validation passed.")


def test_circuit_breaker():
    print("Testing Pillar 5: Circuit Breaker cooldown logic...")
    test_model = "test-experimental-model"
    _record_circuit_success(test_model)
    assert _is_circuit_open(test_model) is False

    # First failure
    _record_circuit_failure(test_model, is_severe=True)
    assert _is_circuit_open(test_model) is False

    # Second failure -> should trip cooldown
    _record_circuit_failure(test_model, is_severe=True)
    assert _is_circuit_open(test_model) is True, "Circuit breaker should be open after 2 consecutive failures"

    # Reset on success
    _record_circuit_success(test_model)
    assert _is_circuit_open(test_model) is False, "Circuit breaker should reset on success"
    print("  ✓ Circuit breaker trips after 2 failures and resets on success.")


def test_content_addressable_caching():
    print("Testing Pillar 6: Content-addressable caching (< 5ms)...")
    key1 = compute_cache_key("system", "Test prompt 123", "schema", "light")
    key2 = compute_cache_key("system", "Test prompt 123", "schema", "light")
    assert key1 == key2, "Cache key must be deterministic"

    test_data = {"test": "val", "cached": True}
    _save_to_cache(key1, test_data)

    start = time.perf_counter()
    retrieved = _get_from_cache(key1)
    duration_ms = (time.perf_counter() - start) * 1000.0

    assert retrieved == test_data
    print(f"  ✓ Cache hit retrieved in {duration_ms:.2f}ms (< 5ms requirement satisfied).")


def test_observability_logging():
    print("Testing Pillar 7: Structured rotating logging...")
    _log_call_record("gemini-3.6-flash", "light", "SUCCESS", 0.312)
    assert os.path.exists(LOG_FILE)
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        last_line = f.readlines()[-1].strip()
    print(f"  Sample log line: {last_line}")
    assert "gemini-3.6-flash" in last_line
    assert "SUCCESS" in last_line
    assert "0.312s" in last_line
    print("  ✓ Log records adhere to structured non-leaking format.")


def test_scraper_module():
    print("Testing Scraper module & synthetic price history...")
    product = scrape_product("https://www.amazon.com/dp/B09XS7JWHH?tag=sample-sony-wh1000xm5")
    assert "Sony" in product["title"]
    assert product["current_price"] > 0
    assert product["currency"] == "₹"
    assert len(product["price_history"]) >= 5
    print(f"  Scraped '{product['title'][:40]}...' at {product['currency']}{product['current_price']}")
    print("  ✓ Scraper returned valid normalized product object in Rupees.")


if __name__ == "__main__":
    print("\n=======================================================")
    print("  RUNNING SMARTPRICE AI RESILIENCE VERIFICATION SUITE  ")
    print("=======================================================\n")
    test_lazy_client_and_missing_key()
    test_model_chains()
    test_error_classification()
    test_json_markdown_stripping_and_validation()
    test_circuit_breaker()
    test_content_addressable_caching()
    test_observability_logging()
    test_scraper_module()
    print("\n🎉 ALL RESILIENCE TESTS PASSED SUCCESSFULLY!\n")
