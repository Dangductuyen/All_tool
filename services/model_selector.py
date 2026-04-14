"""
Model Selector - Smart model selection with priority-based auto-selection.

Features:
- Priority-ordered model lists per engine (fast+cheap first)
- Filter models by capability (generateContent/chat/translate)
- Auto-select best model from available models
- Fallback chain: model A -> model B -> model C
- Never hardcode models - always use API-loaded lists when available
"""
from typing import List, Optional, Dict
from dataclasses import dataclass, field

from utils.logger import log


# ============================================================
# Model Priority Configuration
# ============================================================

# Priority order per engine: first = most preferred (fast + cheap)
# These are used to rank API-loaded models, NOT as hardcoded defaults.
MODEL_PRIORITY = {
    "gemini": [
        "gemini-1.5-flash",      # Priority 1: fast + cheap
        "gemini-2.0-flash",      # Priority 2: newer flash
        "gemini-2.0-flash-lite", # Priority 3: lite variant
        "gemini-1.5-pro",        # Priority 4: pro (slower, more capable)
        "gemini-pro",            # Priority 5: legacy fallback
        "gemini-1.0-pro",        # Priority 6: old fallback
    ],
    "openai": [
        "gpt-4o-mini",           # Priority 1: fast + cheap
        "gpt-4o",                # Priority 2: capable
        "gpt-4-turbo",           # Priority 3: turbo
        "gpt-3.5-turbo",         # Priority 4: legacy cheap
        "gpt-4",                 # Priority 5: original gpt-4
    ],
    "deepl": [
        "default",               # DeepL has no model selection
    ],
    "groq": [
        "mixtral-8x7b-32768",    # Priority 1: fast + good quality
        "llama-3.3-70b-versatile",  # Priority 2: larger, versatile
        "llama-3.1-70b-versatile",  # Priority 3: older llama
        "llama-3.1-8b-instant",     # Priority 4: small, fast
        "gemma2-9b-it",             # Priority 5: gemma
    ],
}

# Keywords that indicate a model is NOT suitable for translation
MODEL_EXCLUDE_KEYWORDS = [
    "embedding", "whisper", "dall-e", "tts", "moderation",
    "aqa", "retrieval", "vision", "guard", "tool-use",
    "davinci", "babbage", "curie", "ada",
]

# Keywords that indicate a model IS suitable for translation (at least one must match)
MODEL_INCLUDE_KEYWORDS = {
    "gemini": ["gemini"],
    "openai": ["gpt", "o1", "o3", "chatgpt"],
    "deepl": ["default"],
    "groq": ["mixtral", "llama", "gemma", "qwen", "deepseek"],
}


@dataclass
class ModelSelection:
    """Result of model selection."""
    engine: str
    selected_model: str
    available_models: List[str] = field(default_factory=list)
    priority_rank: int = -1  # -1 means not in priority list
    reason: str = ""

    @property
    def is_selected(self) -> bool:
        return bool(self.selected_model)


def filter_models(engine: str, raw_models: List[str]) -> List[str]:
    """Filter models to only those suitable for text translation.

    - Removes embedding, vision-only, TTS, whisper models
    - Keeps only models matching engine's include keywords
    """
    if engine == "deepl":
        return ["default"]

    include_keywords = MODEL_INCLUDE_KEYWORDS.get(engine, [])
    filtered = []

    for model in raw_models:
        model_lower = model.lower()

        # Exclude non-translation models
        if any(excl in model_lower for excl in MODEL_EXCLUDE_KEYWORDS):
            continue

        # Include if matches at least one keyword (if keywords defined)
        if include_keywords:
            if any(incl in model_lower for incl in include_keywords):
                filtered.append(model)
        else:
            filtered.append(model)

    return filtered


def rank_models(engine: str, available_models: List[str]) -> List[str]:
    """Rank available models by priority.

    Models in the priority list come first (in priority order),
    followed by other available models alphabetically.
    """
    priority = MODEL_PRIORITY.get(engine, [])
    priority_map = {m: i for i, m in enumerate(priority)}

    # Separate into priority-listed and other
    prioritized = []
    others = []

    for model in available_models:
        # Check exact match first
        if model in priority_map:
            prioritized.append((priority_map[model], model))
            continue

        # Check partial match (e.g. "gemini-1.5-flash-001" matches "gemini-1.5-flash")
        matched = False
        for prio_model, prio_rank in priority_map.items():
            if model.startswith(prio_model) or prio_model.startswith(model):
                prioritized.append((prio_rank, model))
                matched = True
                break

        if not matched:
            others.append(model)

    # Sort by priority rank
    prioritized.sort(key=lambda x: x[0])
    others.sort()

    return [m for _, m in prioritized] + others


def select_best_model(engine: str, available_models: List[str]) -> ModelSelection:
    """Auto-select the best model from available models.

    Steps:
    1. Filter out non-translation models
    2. Rank by priority (fast+cheap first)
    3. Select top-ranked model
    """
    if not available_models:
        # Return first priority model as fallback
        priority = MODEL_PRIORITY.get(engine, [])
        fallback = priority[0] if priority else ""
        return ModelSelection(
            engine=engine,
            selected_model=fallback,
            reason="Khong co model kha dung, dung fallback",
        )

    # Step 1: Filter
    filtered = filter_models(engine, available_models)
    if not filtered:
        # If all filtered out, use first available
        filtered = available_models[:5]

    # Step 2: Rank
    ranked = rank_models(engine, filtered)

    # Step 3: Select top
    selected = ranked[0] if ranked else ""
    priority = MODEL_PRIORITY.get(engine, [])
    rank = -1
    for i, p in enumerate(priority):
        if selected.startswith(p) or p.startswith(selected):
            rank = i
            break

    return ModelSelection(
        engine=engine,
        selected_model=selected,
        available_models=ranked,
        priority_rank=rank,
        reason=f"Auto-selected (priority #{rank + 1})" if rank >= 0 else "Auto-selected (best available)",
    )


def get_fallback_model(engine: str, failed_model: str,
                       available_models: Optional[List[str]] = None) -> Optional[str]:
    """Get the next fallback model after a failure.

    Args:
        engine: AI engine name
        failed_model: The model that just failed
        available_models: List of available models (uses priority list if None)

    Returns:
        Next model to try, or None if no fallback available.
    """
    # Build candidate list
    if available_models:
        candidates = rank_models(engine, filter_models(engine, available_models))
    else:
        candidates = MODEL_PRIORITY.get(engine, [])

    if not candidates:
        return None

    # Find the failed model and return next one
    try:
        # Try exact match first
        idx = candidates.index(failed_model)
        if idx + 1 < len(candidates):
            return candidates[idx + 1]
    except ValueError:
        # Try partial match
        for i, candidate in enumerate(candidates):
            if candidate.startswith(failed_model) or failed_model.startswith(candidate):
                if i + 1 < len(candidates):
                    return candidates[i + 1]
                break

    # If failed model not in list or is last, return first model that isn't the failed one
    for candidate in candidates:
        if candidate != failed_model:
            return candidate

    return None


def get_lighter_model(engine: str, current_model: str,
                      available_models: Optional[List[str]] = None) -> Optional[str]:
    """Get a lighter/cheaper model when quota is exceeded.

    Returns a model that is lower in capability (cheaper) than the current one.
    """
    priority = MODEL_PRIORITY.get(engine, [])
    if not priority:
        return None

    # Find current model position in priority list
    current_rank = -1
    for i, p in enumerate(priority):
        if current_model.startswith(p) or p.startswith(current_model):
            current_rank = i
            break

    if current_rank < 0:
        # Not in priority list, return first priority model
        if available_models:
            filtered = filter_models(engine, available_models)
            ranked = rank_models(engine, filtered)
            return ranked[0] if ranked else priority[0]
        return priority[0]

    # Look for a model with higher index (lower capability/cheaper)
    # In our priority list, higher index = heavier model, but for quota
    # we want to try the lightest model available
    candidates = available_models if available_models else priority
    for model in priority:
        if model != current_model and model in candidates:
            return model

    return None
