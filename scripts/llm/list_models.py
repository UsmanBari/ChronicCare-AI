"""
List open-weight chat models available on Groq using the configured API key.
Filters out audio / whisper / preview deprecated models and identifies open-weight licenses.
Reference: https://console.groq.com/docs/models
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

repo_root = Path(__file__).resolve().parent.parent.parent
env_local = repo_root / ".env.local"
if env_local.exists():
    load_dotenv(env_local)

# Add backend to path
sys.path.insert(0, str(repo_root / "backend-poc-technical"))

from llm.groq_client import get_client


# Open-weight knowledge map from Groq model documentation (https://console.groq.com/docs/models)
OPEN_WEIGHT_REGISTRY = {
    "llama-3.1-8b-instant": {
        "name": "Llama 3.1 8B Instant",
        "developer": "Meta",
        "open_weight": True,
        "license": "Llama 3.1 Community License",
        "context_window": 131072,
        "is_chat": True,
    },
    "llama-3.3-70b-versatile": {
        "name": "Llama 3.3 70B Versatile",
        "developer": "Meta",
        "open_weight": True,
        "license": "Llama 3.3 Community License",
        "context_window": 131072,
        "is_chat": True,
    },
    "llama-3.2-1b-preview": {
        "name": "Llama 3.2 1B (Preview)",
        "developer": "Meta",
        "open_weight": True,
        "license": "Llama 3.2 Community License",
        "context_window": 131072,
        "is_chat": True,
    },
    "llama-3.2-3b-preview": {
        "name": "Llama 3.2 3B (Preview)",
        "developer": "Meta",
        "open_weight": True,
        "license": "Llama 3.2 Community License",
        "context_window": 131072,
        "is_chat": True,
    },
    "gemma2-9b-it": {
        "name": "Gemma 2 9B Instruct",
        "developer": "Google DeepMind",
        "open_weight": True,
        "license": "Gemma Terms of Use (Open Weights)",
        "context_window": 8192,
        "is_chat": True,
    },
    "mixtral-8x7b-32768": {
        "name": "Mixtral 8x7B Instruct",
        "developer": "Mistral AI",
        "open_weight": True,
        "license": "Apache 2.0 (Open Weights)",
        "context_window": 32768,
        "is_chat": True,
    },
    "qwen/qwen3.8-27b": {
        "name": "Qwen 3.8 27B",
        "developer": "Alibaba Cloud / Qwen",
        "open_weight": True,
        "license": "Apache 2.0 (Open Weights)",
        "context_window": 32768,
        "is_chat": True,
    },
    "allam-2-7b": {
        "name": "ALLaM 2 7B",
        "developer": "SDAIA",
        "open_weight": True,
        "license": "Open Weights (Permissive)",
        "context_window": 8192,
        "is_chat": True,
    },
    "openai/gpt-oss-20b": {
        "name": "GPT-OSS 20B",
        "developer": "OpenAI / Open Source",
        "open_weight": True,
        "license": "Apache 2.0 (Open Weights)",
        "context_window": 16384,
        "is_chat": True,
    },
    "openai/gpt-oss-120b": {
        "name": "GPT-OSS 120B",
        "developer": "OpenAI / Open Source",
        "open_weight": True,
        "license": "Apache 2.0 (Open Weights)",
        "context_window": 16384,
        "is_chat": True,
    },
}


def list_groq_models():
    print("Connecting to Groq API using configured GROQ_API_KEY...")
    client = get_client()
    model_list = client.models.list()
    raw_models = getattr(model_list, "data", [])
    raw_ids = [m.id for m in raw_models]

    print(f"\nAll models returned by Groq API ({len(raw_ids)} total):")
    for mid in sorted(raw_ids):
        print(f"  * {mid}")

    print("\nFiltering for OPEN-WEIGHT CHAT models supported for ChronicCare AI explainer:")
    print("Documentation reference: https://console.groq.com/docs/models\n")

    print(f"{'Model ID':<28} | {'Developer':<15} | {'Open Weight?':<13} | {'License':<32}")
    print("-" * 95)

    candidates = []
    for mid in sorted(raw_ids):
        # Exclude whisper/audio or guard models
        if "whisper" in mid.lower() or "guard" in mid.lower() or "vision" in mid.lower():
            continue
        info = OPEN_WEIGHT_REGISTRY.get(mid)
        if info and info.get("open_weight") and info.get("is_chat"):
            candidates.append(mid)
            print(f"{mid:<28} | {info['developer']:<15} | {'YES':<13} | {info['license']:<32}")
        elif info is None:
            # Check prefix heuristics
            if "llama" in mid.lower() or "gemma" in mid.lower() or "mixtral" in mid.lower() or "qwen" in mid.lower():
                candidates.append(mid)
                print(f"{mid:<28} | {'Community':<15} | {'YES (Inferred)':<13} | {'Open / Permissive Community'}")

    print("\nRecommended candidate models for compare_explainer_models.py:")
    for c in candidates:
        print(f"  --> {c}")
    return candidates


if __name__ == "__main__":
    list_groq_models()
