"""
SmartPrice AI - Resilient Gemini API Engine
Implements the 7 Architectural Pillars:
1. Core Rules & Security (No key/prompt leaks, lazy client init, retry bypass, timeout)
2. Multi-Model Fallback Chains (Tiered routing: light vs heavy)
3. Intelligent HTTP Error Classification (401/403 abort, 404 instant skip, 400 thinking retry, 429/5xx exponential backoff)
4. Output Validation & Self-Healing JSON (Strip markdown fences, single retry with temperature=0 & prompt append, schema validation)
5. Speed & Load Protection (Thread-safe rate limiter, 60s circuit breaker after 2 consecutive 429/503/timeouts)
6. Content-Addressable Caching & Offline Fallback (SHA-256 excluding key/model, <5ms cache hit, demo_data/ fallback)
7. Observability & Logging (RotatingFileHandler max 1MB x 3 backups, get_last_call_info())
"""

import os
import re
import time
import json
import random
import hashlib
import logging
import threading
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, List, Optional, Tuple, Union

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# ==============================================================================
# Pillar 7: Observability & Logging Setup
# ==============================================================================
LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOGS_DIR, "calls.log")

_call_logger = logging.getLogger("gemini_calls")
_call_logger.setLevel(logging.INFO)
_call_logger.propagate = False

if not _call_logger.handlers:
    _handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=1 * 1024 * 1024,  # 1 MB
        backupCount=3,
        encoding="utf-8"
    )
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _call_logger.addHandler(_handler)

# Cache directory & Demo data directory
CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")
DEMO_DIR = os.path.join(os.path.dirname(__file__), "demo_data")
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(DEMO_DIR, exist_ok=True)

# Thread-local storage for last call metadata
_thread_local = threading.local()

# ==============================================================================
# Pillar 5: Speed & Load Protection (Rate Limiter & Circuit Breaker)
# ==============================================================================
_rate_limiter_lock = threading.Lock()
_last_api_call_timestamp: float = 0.0

_circuit_lock = threading.Lock()
_circuit_consecutive_failures: Dict[str, int] = {}
_circuit_cooldown_expiry: Dict[str, float] = {}


def _enforce_rate_limit():
    """Enforces minimum interval between API calls via thread-safe lock."""
    global _last_api_call_timestamp
    min_interval = float(os.getenv("GEMINI_MIN_INTERVAL_SECONDS", "1.0"))
    with _rate_limiter_lock:
        now = time.time()
        elapsed = now - _last_api_call_timestamp
        if elapsed < min_interval:
            sleep_time = min_interval - elapsed
            time.sleep(sleep_time)
        _last_api_call_timestamp = time.time()


def _is_circuit_open(model: str) -> bool:
    """Checks if the circuit breaker is currently tripped for this model."""
    with _circuit_lock:
        cooldown = _circuit_cooldown_expiry.get(model, 0.0)
        return time.time() < cooldown


def _record_circuit_failure(model: str, is_severe: bool):
    """
    Increments failure count for model. If 2 consecutive 429/503/timeouts occur,
    places the model in 60-second cooldown.
    """
    with _circuit_lock:
        if is_severe:
            current = _circuit_consecutive_failures.get(model, 0) + 1
            _circuit_consecutive_failures[model] = current
            if current >= 2:
                _circuit_cooldown_expiry[model] = time.time() + 60.0
        else:
            _circuit_consecutive_failures[model] = 0


def _record_circuit_success(model: str):
    """Resets consecutive failure count and clears cooldown for the model."""
    with _circuit_lock:
        _circuit_consecutive_failures[model] = 0
        _circuit_cooldown_expiry[model] = 0.0


def _log_call_record(model: str, task: str, outcome: str, elapsed_seconds: float):
    """
    Pillar 1 & 7: Writes structured log record with strict redaction of keys & prompts.
    Format: <timestamp_iso> | <model> | <task> | <outcome_or_error_code> | <seconds_taken>s
    """
    iso_time = datetime.now(timezone.utc).isoformat()
    record = f"{iso_time} | {model} | {task} | {outcome} | {elapsed_seconds:.3f}s"
    _call_logger.info(record)


# ==============================================================================
# Pillar 6: Content-Addressable Caching
# ==============================================================================
def compute_cache_key(system_instruction: str, prompt: str, schema_str: str, task: str) -> str:
    """
    Pillar 6: Content-addressable cache key.
    SHA-256(system_instruction + prompt + schema + task).
    EXPLICITLY EXCLUDES model name and API key.
    """
    content = f"{system_instruction or ''}|{prompt}|{schema_str or ''}|{task}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _get_from_cache(cache_key: str) -> Optional[Any]:
    cache_path = os.path.join(CACHE_DIR, f"{cache_key}.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("result")
        except Exception:
            # Corrupt cache file: ignore gracefully
            pass
    return None


def _save_to_cache(cache_key: str, result: Any):
    cache_path = os.path.join(CACHE_DIR, f"{cache_key}.json")
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump({"result": result, "cached_at": time.time()}, f, ensure_ascii=False)
    except Exception:
        pass


def _find_offline_demo_fallback(cache_key: str, prompt: str) -> Optional[Any]:
    """
    Searches .cache/ and demo_data/ for matching keys or semantic demo fallbacks.
    """
    # 1. Exact cache key check in demo_data/
    demo_path = os.path.join(DEMO_DIR, f"{cache_key}.json")
    if os.path.exists(demo_path):
        try:
            with open(demo_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("result", data)
        except Exception:
            pass

    # 2. Match by product keyword in demo_data/ catalog
    prompt_lower = prompt.lower()
    for fname in os.listdir(DEMO_DIR):
        if fname.endswith(".json"):
            name_base = fname.replace(".json", "").lower()
            if name_base in prompt_lower or any(kw in prompt_lower for kw in name_base.split("_")):
                try:
                    with open(os.path.join(DEMO_DIR, fname), "r", encoding="utf-8") as f:
                        data = json.load(f)
                        return data.get("result", data)
                except Exception:
                    pass

    # 3. Generic default deal analysis demo
    default_demo = os.path.join(DEMO_DIR, "default_deal.json")
    if os.path.exists(default_demo):
        try:
            with open(default_demo, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("result", data)
        except Exception:
            pass

    return None


# ==============================================================================
# Pillar 1 & 2: Lazy Client, Model Chains, and Options
# ==============================================================================
_lazy_client_instance = None
_lazy_client_key: Optional[str] = None


def get_model_chain(task: str = "light") -> List[str]:
    """Reads comma-separated model chains from environment with exact defaults."""
    if task == "heavy":
        chain_env = os.getenv(
            "GEMINI_MODEL_CHAIN_HEAVY",
            "gemini-3.6-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite,gemini-flash-lite-latest"
        )
    else:
        chain_env = os.getenv(
            "GEMINI_MODEL_CHAIN_LIGHT",
            "gemini-3.5-flash-lite,gemini-3.1-flash-lite,gemini-3.6-flash,gemini-flash-lite-latest"
        )
    models = [m.strip() for m in chain_env.split(",") if m.strip()]
    return models if models else ["gemini-3.6-flash", "gemini-3.5-flash-lite"]


def _get_gemini_client(api_key: Optional[str] = None):
    """
    Pillar 1: Lazy initialization.
    Never crashes on import. Raises friendly ValueError if key is missing.
    Disables SDK retries (attempts=1) and enforces timeout.
    """
    global _lazy_client_instance, _lazy_client_key

    active_key = api_key or os.getenv("GEMINI_API_KEY")
    if not active_key or active_key.strip() in ("", "your_gemini_api_key_here"):
        raise ValueError("GEMINI_API_KEY is not configured. Please set it in .env or via the Settings menu.")

    timeout_sec = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "35"))

    if _lazy_client_instance is not None and _lazy_client_key == active_key:
        return _lazy_client_instance

    try:
        from google import genai
        from google.genai import types

        # Disable internal SDK retries (attempts=1) and enforce strict timeout
        http_options = types.HttpOptions(
            timeout=int(timeout_sec * 1000),  # milliseconds
            retry_options=types.HttpRetryOptions(attempts=1)
        )
        client = genai.Client(api_key=active_key, http_options=http_options)
        _lazy_client_instance = client
        _lazy_client_key = active_key
        return client
    except ImportError:
        # Fallback to direct HTTP client if google-genai is being installed or not found
        return DirectGeminiHttpClient(active_key, timeout_sec)


class DirectGeminiHttpClient:
    """Lightweight direct HTTPS client conforming to the same interface when SDK is absent."""
    def __init__(self, api_key: str, timeout_sec: float):
        self.api_key = api_key
        self.timeout_sec = timeout_sec

    def generate_content(self, model: str, contents: str, system_instruction: Optional[str] = None,
                         temperature: Optional[float] = None, disable_thinking: bool = False):
        import requests
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": contents}]}],
            "generationConfig": {}
        }
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        if temperature is not None:
            payload["generationConfig"]["temperature"] = temperature
        if disable_thinking:
            payload["generationConfig"]["thinkingConfig"] = {"thinkingBudget": 0}

        headers = {"Content-Type": "application/json"}
        resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout_sec)
        if resp.status_code != 200:
            err = Exception(f"HTTP {resp.status_code}: {resp.text}")
            err.status_code = resp.status_code
            err.headers = resp.headers
            raise err

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError("Empty or blocked response from model")

        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts)
        finish_reason = candidates[0].get("finishReason", "STOP")

        class MockResponse:
            def __init__(self, text, finish_reason):
                self.text = text
                self.finish_reason = finish_reason
                self.candidates = candidates

        return MockResponse(text, finish_reason)


# ==============================================================================
# Pillar 3: Intelligent HTTP Error Classification
# ==============================================================================
class ErrorClassification:
    def __init__(self, action: str, status_code: Optional[int] = None, is_severe: bool = False,
                 message: str = "", retry_after: Optional[float] = None):
        self.action = action  # "ABORT", "NEXT_MODEL_INSTANT", "RETRY_DISABLE_THINKING", "RETRY_BACKOFF", "NEXT_MODEL"
        self.status_code = status_code
        self.is_severe = is_severe
        self.message = message
        self.retry_after = retry_after


def _classify_error(exc: Exception) -> ErrorClassification:
    """
    Classifies errors according to Pillar 3:
    - 401 / 403: Stop immediately. Zero retries. Raise friendly 'API key invalid or unauthorized'.
    - 404: Move to next model in chain immediately with 0ms sleep.
    - 400 with 'thinking' in message: Retry same model once with thinking_config disabled.
    - Other 400: Stop immediately and report error.
    - 429, 500, 502, 503, 504, Timeouts, Connection Errors: Retry same model up to 2 times with exponential backoff.
    """
    msg = str(exc).lower()
    status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)

    # If status code not directly on exception, extract via regex from message
    if not status_code:
        match = re.search(r"\b(400|401|403|404|429|500|502|503|504)\b", msg)
        if match:
            try:
                status_code = int(match.group(1))
            except ValueError:
                pass

    # Inspect Retry-After header if present
    retry_after = None
    headers = getattr(exc, "headers", None)
    if headers and "Retry-After" in headers:
        try:
            val = float(headers["Retry-After"])
            if val < 10.0:
                retry_after = val
        except (ValueError, TypeError):
            pass

    if status_code in (401, 403) or "unauthorized" in msg or "invalid api key" in msg or "permissiondenied" in msg:
        return ErrorClassification(
            action="ABORT",
            status_code=status_code or 401,
            is_severe=False,
            message="API key invalid or unauthorized. Please verify your GEMINI_API_KEY in .env or Settings."
        )

    if status_code == 404 or "not found" in msg or "is not supported" in msg:
        return ErrorClassification(
            action="NEXT_MODEL_INSTANT",
            status_code=404,
            is_severe=False,
            message="Model retired or not found."
        )

    if status_code == 400:
        if "thinking" in msg or "thinking_config" in msg or "thinkingbudget" in msg:
            return ErrorClassification(
                action="RETRY_DISABLE_THINKING",
                status_code=400,
                is_severe=False,
                message="Thinking config not supported on this model, retrying with thinking disabled."
            )
        return ErrorClassification(
            action="ABORT",
            status_code=400,
            is_severe=False,
            message=f"Bad Request: {str(exc)}"
        )

    # 429, 500, 502, 503, 504, Timeouts, Connection Errors
    is_timeout = "timeout" in msg or "timed out" in msg or isinstance(exc, (TimeoutError, OSError))
    is_transient = status_code in (429, 500, 502, 503, 504) or "resourceexhausted" in msg or "overloaded" in msg or is_timeout

    if is_transient:
        return ErrorClassification(
            action="RETRY_BACKOFF",
            status_code=status_code or (504 if is_timeout else 500),
            is_severe=(status_code in (429, 503) or is_timeout),
            message=f"Transient error ({status_code or 'timeout'}), eligible for exponential retry.",
            retry_after=retry_after
        )

    # Unknown generic error: treat as next model candidate
    return ErrorClassification(
        action="NEXT_MODEL",
        status_code=status_code or 500,
        is_severe=False,
        message=str(exc)
    )


# ==============================================================================
# Pillar 4: Output Validation & Self-Healing JSON Helpers
# ==============================================================================
def _clean_json_markdown(text: str) -> str:
    """Strips markdown code fences (```json ... ```) from model response."""
    text = text.strip()
    if text.startswith("```"):
        # Match ```json or ``` at beginning and ``` at end
        match = re.search(r"^```(?:json)?\s*\n?(.*?)\n?```$", text, re.DOTALL)
        if match:
            return match.group(1).strip()
    return text


def _validate_schema(data: Dict[str, Any], required_fields: Optional[List[str]]) -> bool:
    """Validates required schema fields exist in parsed dictionary."""
    if not required_fields:
        return True
    if not isinstance(data, dict):
        return False
    return all(field in data for field in required_fields)


# ==============================================================================
# Public API: Resilient Generation Functions
# ==============================================================================
def get_last_call_info() -> Dict[str, Any]:
    """
    Pillar 7: Observability helper returning metadata for the most recent call.
    {"model_used": str, "source": "live" | "cache" | "demo", "attempts": int, "fell_back": bool, "seconds": float}
    """
    return getattr(_thread_local, "last_call_info", {
        "model_used": "none",
        "source": "cache",
        "attempts": 0,
        "fell_back": False,
        "seconds": 0.0
    })


def _set_last_call_info(model_used: str, source: str, attempts: int, fell_back: bool, seconds: float):
    _thread_local.last_call_info = {
        "model_used": model_used,
        "source": source,
        "attempts": attempts,
        "fell_back": fell_back,
        "seconds": round(seconds, 4)
    }


def generate_text(
    prompt: str,
    system_instruction: Optional[str] = None,
    task: str = "light",
    api_key: Optional[str] = None,
    temperature: Optional[float] = None
) -> str:
    """
    Executes resilient text generation with multi-model fallback, rate limiting,
    and content-addressable caching.
    """
    start_time = time.time()
    cache_key = compute_cache_key(system_instruction or "", prompt, "", task)

    # 1. Check content-addressable cache (< 5ms response)
    cached_val = _get_from_cache(cache_key)
    if cached_val is not None and isinstance(cached_val, str):
        elapsed = time.time() - start_time
        _set_last_call_info("cache", "cache", 0, False, elapsed)
        return cached_val

    # 2. Prepare model chain
    models = get_model_chain(task=task)

    # If all models in chain are in cooldown, bypass the skip to allow attempts
    all_in_cooldown = all(_is_circuit_open(m) for m in models)

    attempts_count = 0
    fell_back = False
    model_outcomes: List[str] = []

    for model_index, model in enumerate(models):
        if _is_circuit_open(model) and not all_in_cooldown:
            model_outcomes.append(f"{model}: skipped (circuit breaker cooldown)")
            continue

        if model_index > 0:
            fell_back = True

        disable_thinking = False

        # Attempt up to 3 tries per model (1 initial + 2 retries for transient errors)
        for retry_attempt in range(3):
            attempts_count += 1
            call_start = time.time()
            try:
                _enforce_rate_limit()
                client = _get_gemini_client(api_key)

                if hasattr(client, "models"):
                    from google.genai import types
                    config_kwargs: Dict[str, Any] = {}
                    if system_instruction:
                        config_kwargs["system_instruction"] = system_instruction
                    if temperature is not None:
                        config_kwargs["temperature"] = temperature
                    if disable_thinking:
                        config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

                    config = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None
                    response = client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=config
                    )
                else:
                    response = client.generate_content(
                        model=model,
                        contents=prompt,
                        system_instruction=system_instruction,
                        temperature=temperature,
                        disable_thinking=disable_thinking
                    )

                # Reject empty, blocked, or None responses
                if not response or not getattr(response, "text", None) or not response.text.strip():
                    raise ValueError(f"Empty or blocked response from model {model}")

                call_elapsed = time.time() - call_start
                _log_call_record(model, task, "SUCCESS", call_elapsed)
                _record_circuit_success(model)

                result_text = response.text.strip()
                _save_to_cache(cache_key, result_text)
                total_elapsed = time.time() - start_time
                _set_last_call_info(model, "live", attempts_count, fell_back, total_elapsed)
                return result_text

            except Exception as exc:
                call_elapsed = time.time() - call_start
                classification = _classify_error(exc)
                _log_call_record(model, task, f"ERROR_{classification.status_code or 'FAIL'}", call_elapsed)

                if classification.action == "ABORT":
                    raise ValueError(classification.message)

                if classification.action == "NEXT_MODEL_INSTANT":
                    model_outcomes.append(f"{model}: 404 retired/not found")
                    break  # Break retry loop, fall forward to next model with 0ms sleep

                if classification.action == "RETRY_DISABLE_THINKING":
                    disable_thinking = True
                    continue  # Retry same model with thinking disabled

                if classification.action == "RETRY_BACKOFF":
                    _record_circuit_failure(model, is_severe=classification.is_severe)
                    if retry_attempt < 2:
                        # Exponential backoff (1s, 2s + 0-0.5s jitter) or respect Retry-After
                        if classification.retry_after is not None and classification.retry_after < 10.0:
                            sleep_duration = classification.retry_after
                        else:
                            sleep_duration = (2 ** retry_attempt) + random.uniform(0, 0.5)
                        time.sleep(sleep_duration)
                        continue
                    else:
                        model_outcomes.append(f"{model}: failed after {retry_attempt + 1} retries ({exc})")
                        break  # Fall forward to next model

                # Generic next model
                model_outcomes.append(f"{model}: {str(exc)}")
                break

    # If all models fail: check offline fallback before raising
    offline_data = _find_offline_demo_fallback(cache_key, prompt)
    if offline_data:
        total_elapsed = time.time() - start_time
        _set_last_call_info("demo_fallback", "demo", attempts_count, True, total_elapsed)
        if isinstance(offline_data, str):
            return offline_data
        return json.dumps(offline_data)

    raise RuntimeError(
        f"All models in fallback chain failed for task '{task}'. Details: " + "; ".join(model_outcomes)
    )


def generate_json(
    prompt: str,
    system_instruction: Optional[str] = None,
    required_fields: Optional[List[str]] = None,
    task: str = "light",
    api_key: Optional[str] = None,
    temperature: Optional[float] = None
) -> Dict[str, Any]:
    """
    Pillar 4: Robust JSON Generation with Self-Healing:
    - Strips markdown code fences (```json ... ```)
    - If JSON parsing fails or finish reason is MAX_TOKENS:
      Triggers self-healing retry ONCE on the same model with temperature=0
      and prompt appended with: "Return only valid JSON matching the schema."
    - Validates required fields are present in parsed dictionary.
    """
    start_time = time.time()
    schema_str = ",".join(sorted(required_fields)) if required_fields else ""
    cache_key = compute_cache_key(system_instruction or "", prompt, schema_str, task)

    # 1. Content-addressable cache (< 5ms response)
    cached_val = _get_from_cache(cache_key)
    if cached_val is not None and isinstance(cached_val, dict):
        if _validate_schema(cached_val, required_fields):
            elapsed = time.time() - start_time
            _set_last_call_info("cache", "cache", 0, False, elapsed)
            return cached_val

    # 2. Prepare model chain
    models = get_model_chain(task=task)
    all_in_cooldown = all(_is_circuit_open(m) for m in models)

    attempts_count = 0
    fell_back = False
    model_outcomes: List[str] = []

    for model_index, model in enumerate(models):
        if _is_circuit_open(model) and not all_in_cooldown:
            model_outcomes.append(f"{model}: skipped (circuit breaker cooldown)")
            continue

        if model_index > 0:
            fell_back = True

        disable_thinking = False

        for retry_attempt in range(3):
            attempts_count += 1
            call_start = time.time()
            try:
                _enforce_rate_limit()
                client = _get_gemini_client(api_key)

                current_prompt = prompt
                current_temp = temperature

                # Inner function to execute call on active client
                def _do_call(p: str, temp: Optional[float]):
                    if hasattr(client, "models"):
                        from google.genai import types
                        cfg: Dict[str, Any] = {"response_mime_type": "application/json"}
                        if system_instruction:
                            cfg["system_instruction"] = system_instruction
                        if temp is not None:
                            cfg["temperature"] = temp
                        if disable_thinking:
                            cfg["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
                        return client.models.generate_content(
                            model=model,
                            contents=p,
                            config=types.GenerateContentConfig(**cfg)
                        )
                    else:
                        return client.generate_content(
                            model=model,
                            contents=p,
                            system_instruction=system_instruction,
                            temperature=temp,
                            disable_thinking=disable_thinking
                        )

                response = _do_call(current_prompt, current_temp)

                if not response or not getattr(response, "text", None) or not response.text.strip():
                    raise ValueError(f"Empty or blocked response from model {model}")

                raw_text = response.text.strip()
                cleaned_text = _clean_json_markdown(raw_text)

                finish_reason = getattr(response, "finish_reason", "STOP")
                # Self-healing attempt flag
                parsed_json = None
                needs_healing = False

                if finish_reason == "MAX_TOKENS":
                    needs_healing = True
                else:
                    try:
                        parsed_json = json.loads(cleaned_text)
                        if not _validate_schema(parsed_json, required_fields):
                            needs_healing = True
                    except Exception:
                        needs_healing = True

                # Self-healing retry ONCE on the same model
                if needs_healing:
                    healing_prompt = current_prompt + "\n\nReturn only valid JSON matching the schema."
                    heal_resp = _do_call(healing_prompt, temp=0.0)
                    if heal_resp and getattr(heal_resp, "text", None):
                        cleaned_heal = _clean_json_markdown(heal_resp.text.strip())
                        try:
                            parsed_json = json.loads(cleaned_heal)
                            if not _validate_schema(parsed_json, required_fields):
                                raise ValueError("Self-healing returned JSON missing required schema fields.")
                        except Exception as heal_err:
                            raise ValueError(f"Self-healing JSON parse failed: {heal_err}")
                    else:
                        raise ValueError("Self-healing returned empty response")

                # Successful validated result
                call_elapsed = time.time() - call_start
                _log_call_record(model, task, "SUCCESS", call_elapsed)
                _record_circuit_success(model)

                _save_to_cache(cache_key, parsed_json)
                total_elapsed = time.time() - start_time
                _set_last_call_info(model, "live", attempts_count, fell_back, total_elapsed)
                return parsed_json

            except Exception as exc:
                call_elapsed = time.time() - call_start
                classification = _classify_error(exc)
                _log_call_record(model, task, f"ERROR_{classification.status_code or 'FAIL'}", call_elapsed)

                if classification.action == "ABORT":
                    raise ValueError(classification.message)

                if classification.action == "NEXT_MODEL_INSTANT":
                    model_outcomes.append(f"{model}: 404 retired/not found")
                    break

                if classification.action == "RETRY_DISABLE_THINKING":
                    disable_thinking = True
                    continue

                if classification.action == "RETRY_BACKOFF":
                    _record_circuit_failure(model, is_severe=classification.is_severe)
                    if retry_attempt < 2:
                        sleep_duration = (
                            classification.retry_after
                            if classification.retry_after is not None and classification.retry_after < 10.0
                            else (2 ** retry_attempt) + random.uniform(0, 0.5)
                        )
                        time.sleep(sleep_duration)
                        continue
                    else:
                        model_outcomes.append(f"{model}: backoff exhausted ({exc})")
                        break

                model_outcomes.append(f"{model}: {str(exc)}")
                break

    # Offline / Demo fallback on failure
    offline_data = _find_offline_demo_fallback(cache_key, prompt)
    if offline_data and isinstance(offline_data, dict):
        total_elapsed = time.time() - start_time
        _set_last_call_info("demo_fallback", "demo", attempts_count, True, total_elapsed)
        return offline_data

    raise RuntimeError(
        f"All models in fallback chain failed for JSON task '{task}'. Details: " + "; ".join(model_outcomes)
    )


# ==============================================================================
# Domain Services: Deal Verdict Engine & Natural Language Advisor
# ==============================================================================
SYSTEM_INSTRUCTION_VERDICT = (
    "You are SmartPrice AI, an elite retail deal analyst and price tracking intelligence engine. "
    "Your mission is to protect online shoppers from inflated MSRPs, artificial discounts, and bad purchase timing. "
    "All currency amounts are strictly in Indian Rupees (₹). You must always quote, evaluate, and format prices in Indian Rupees (₹) and NEVER in US Dollars ($). "
    "You evaluate current prices against historical price ranges, upcoming Indian retail sale cycles (e.g. Great Indian Festival, "
    "Big Billion Days, Diwali sales, Republic Day/Independence Day sales, seasonal clearances), and authentic customer reviews. "
    "Always return crisp, fact-based insights formatted strictly according to the requested JSON schema."
)

VERDICT_REQUIRED_FIELDS = [
    "verdict",
    "rationale",
    "deal_integrity_score",
    "pros",
    "cons",
    "recommended_target_price",
    "price_trend_prediction"
]


def analyze_deal(
    product_title: str,
    current_price: float,
    original_price: Optional[float] = None,
    currency: str = "₹",
    merchant: str = "Store",
    rating: Optional[float] = None,
    reviews_summary: str = "",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes the Gemini AI Verdict Engine with structured JSON schema:
    a) 'BUY NOW' / 'WAIT' / 'RISKY' verdict score.
    b) 2-sentence rationale based on estimated price trends & upcoming sale cycles.
    c) 'Deal Integrity Score' (0-100 detecting inflated base prices/fake discounts).
    d) 3-bullet summary of top pros and cons from customer reviews.
    e) Recommended target price and price trend prediction.
    """
    orig_text = f"{currency}{original_price}" if original_price else "Not specified"
    prompt = f"""
Analyze this e-commerce deal:
- Product Title: {product_title}
- Merchant: {merchant}
- Current Price: {currency}{current_price}
- Stated List/Original Price: {orig_text}
- Customer Rating: {rating or 'N/A'}/5.0
- Customer Reviews Digest / Metadata: {reviews_summary or 'No specific reviews provided'}

Return a valid JSON object matching EXACTLY these keys:
{{
  "verdict": "BUY NOW" | "WAIT" | "RISKY",
  "rationale": "Exactly 2 concise sentences explaining why based on price trends and upcoming sale cycles.",
  "deal_integrity_score": integer between 0 and 100 representing how genuine the discount is (100 = 100% genuine historic low, 20 = fake markdown on inflated MSRP),
  "pros": ["Pro 1 (max 10 words)", "Pro 2 (max 10 words)", "Pro 3 (max 10 words)"],
  "cons": ["Con 1 (max 10 words)", "Con 2 (max 10 words)", "Con 3 (max 10 words)"],
  "recommended_target_price": float representing the optimal buy price,
  "price_trend_prediction": "Likely to drop within 30 days" | "At historic low" | "Stable price" | "Price artificially inflated"
}}
"""
    return generate_json(
        prompt=prompt,
        system_instruction=SYSTEM_INSTRUCTION_VERDICT,
        required_fields=VERDICT_REQUIRED_FIELDS,
        task="light",
        api_key=api_key,
        temperature=0.2
    )


def ask_advisor(
    question: str,
    product_title: str,
    current_price: float,
    currency: str = "₹",
    merchant: str = "Store",
    verdict_data: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Natural language deal advisor (e.g. 'Should I buy it now?').
    Uses task='heavy' for deep contextual reasoning.
    """
    context = (
        f"Product: {product_title}\n"
        f"Current Price: {currency}{current_price}\n"
        f"Merchant: {merchant}\n"
    )
    if verdict_data:
        context += (
            f"Current AI Verdict: {verdict_data.get('verdict')}\n"
            f"Deal Integrity Score: {verdict_data.get('deal_integrity_score')}%\n"
            f"Rationale: {verdict_data.get('rationale')}\n"
        )

    prompt = f"""
{context}

The shopper is asking the following question in natural language:
"{question}"

Provide a direct, conversational, and highly practical answer (under 120 words).
Ensure all price references and advice are in Indian Rupees (₹). Never mention or use dollars ($).
Also return an immediate recommendation ('BUY NOW', 'WAIT', or 'RISKY') and a confidence score (0-100).

Return as valid JSON:
{{
  "answer": "Your direct answer to the user's question.",
  "recommendation": "BUY NOW" | "WAIT" | "RISKY",
  "confidence": integer between 0 and 100,
  "key_takeaway": "One short sentence punchline."
}}
"""
    return generate_json(
        prompt=prompt,
        system_instruction=SYSTEM_INSTRUCTION_VERDICT,
        required_fields=["answer", "recommendation", "confidence", "key_takeaway"],
        task="heavy",
        api_key=api_key,
        temperature=0.3
    )
