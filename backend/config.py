# Configuration settings for ConstructionOS AI agents

import os

# Default model configuration for Google GenAI SDK calls.
# WARNING: Free-tier RPD quota for gemini-3.5-flash-lite on this project is UNCONFIRMED.
# No billing account is linked. Treat quota as unknown and unreliable until
# confirmed via: https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas
# To switch models, change this single constant — all 4 agents import from here.
MODEL_NAME = "gemini-3.5-flash-lite"


def use_mock_llm() -> bool:
    """
    Returns True when USE_MOCK_LLM=true is set in the environment,
    enabling fully deterministic demo mode with zero Gemini API calls.
    Reads directly from env vars (loaded by dotenv at startup) and also
    checks the .env file directly as a fallback for processes that don't
    use python-dotenv.
    """
    val = os.getenv("USE_MOCK_LLM", "").strip().lower()
    if val == "true":
        return True
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
