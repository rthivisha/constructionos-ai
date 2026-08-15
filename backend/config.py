import os
import time
import logging

logger = logging.getLogger(__name__)

# Default model configuration for Google GenAI SDK calls.
# WARNING: Free-tier RPD quota for gemini-3.5-flash-lite on this project is UNCONFIRMED.
# No billing account is linked. Treat quota as unknown and unreliable until
# confirmed via: https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas
# To switch models, change this single constant — all 4 agents import from here.
MODEL_NAME = "gemini-3.5-flash-lite"

# Assumed daily wage rate per worker (₹) - placeholder assumption for labour cost calculations
ASSUMED_DAILY_WAGE_PER_WORKER = 1500


def is_rate_limit_error(e: Exception) -> bool:
    """
    Checks if an exception represents an HTTP 429 / RESOURCE_EXHAUSTED rate limit error.
    """
    err_str = str(e).lower()
    return (
        "429" in err_str
        or "resource_exhausted" in err_str
        or "rate limit" in err_str
        or "quota" in err_str
        or getattr(e, "code", None) == 429
    )


def call_gemini_with_retry(
    client,
    model: str,
    contents,
    config=None,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0
):
    """
    Calls client.models.generate_content with exponential backoff retry on 429/RESOURCE_EXHAUSTED errors.
    - Initial delay: 1.0s
    - Backoff factor: 2.0x (1.0s -> 2.0s -> 4.0s)
    - Max retries: 3 attempts
    If retries are exhausted or a non-retryable error occurs, re-raises the exception for per-request fallback.
    """
    delay = initial_delay
    last_exception = None
    for attempt in range(1, max_retries + 1):
        try:
            if config is not None:
                return client.models.generate_content(model=model, contents=contents, config=config)
            return client.models.generate_content(model=model, contents=contents)
        except Exception as e:
            last_exception = e
            if is_rate_limit_error(e) and attempt < max_retries:
                logger.warning(
                    f"Gemini API rate limit (429/RESOURCE_EXHAUSTED) hit on attempt {attempt}/{max_retries}. "
                    f"Retrying in {delay:.1f}s... Details: {e}"
                )
                time.sleep(delay)
                delay *= backoff_factor
            else:
                logger.error(f"Gemini API call failed on attempt {attempt}/{max_retries}: {e}")
                raise e
    if last_exception:
        raise last_exception


def use_mock_llm() -> bool:
    """
    Returns True when USE_MOCK_LLM=true is set in the environment,
    enabling fully deterministic demo mode with zero Gemini API calls.
    Reads directly from env vars (loaded by dotenv at startup) and also
    checks the .env file directly as a fallback for processes that don't
    use python-dotenv.
    """
    val = os.getenv("USE_MOCK_LLM", "").strip().lower()
    if val:
        return val == "true"
    # Direct file fallback
    for dotenv_path in ["backend/.env", ".env"]:
        if os.path.exists(dotenv_path):
            try:
                with open(dotenv_path, "r") as f:
                    for line in f:
                        stripped = line.strip()
                        if stripped.startswith("USE_MOCK_LLM="):
                            v = stripped.split("=", 1)[1].strip().strip('"').strip("'").lower()
                            if v == "true":
                                return True
            except Exception:
                pass
    return False

