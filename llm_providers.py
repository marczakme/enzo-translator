import os
from typing import Optional, List, Dict, Tuple

from openai import OpenAI
from google import genai
from google.genai import errors as genai_errors


def _join_messages_to_text(messages: List[Dict[str, str]]) -> Tuple[str, str]:
    system_parts, user_parts = [], []
    for m in messages:
        role = (m.get("role") or "").lower().strip()
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if role == "system":
            system_parts.append(content)
        else:
            user_parts.append(content)
    system_text = "\n\n".join(system_parts).strip()
    user_text = "\n\n".join(user_parts).strip() or " "
    return system_text, user_text


def _clip(text: str, max_chars: int) -> str:
    if not text:
        return text
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 200] + "\n\n[...truncated due to length...]\n"


# -------------------------
# Clients
# -------------------------

def _openai_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Brak OPENAI_API_KEY w secrets/ENV.")
    return OpenAI(api_key=api_key)


def _qwen_client() -> OpenAI:
    """
    Qwen (Alibaba Model Studio / DashScope) via OpenAI-compatible protocol:
    endpoint differs by region (intl vs Beijing). :contentReference[oaicite:1]{index=1}
    """
    api_key = os.environ.get("QWEN_API_KEY")
    if not api_key:
        raise RuntimeError("Brak QWEN_API_KEY w secrets/ENV.")

    # IMPORTANT: Alibaba docs show endpoints including /chat/completions. :contentReference[oaicite:2]{index=2}
    base_url = os.environ.get("QWEN_BASE_URL") or "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    return OpenAI(api_key=api_key, base_url=base_url)


def _gemini_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Brak GEMINI_API_KEY w secrets/ENV.")
    return genai.Client(api_key=api_key)


# -------------------------
# Main API
# -------------------------

def chat_llm(
    provider: str,
    messages: list,
    temperature: float = 0.2,
    model_hint: Optional[str] = None,
) -> str:
    """
    provider: openai | gemini | qwen
    """

    provider = provider.lower().strip()
    system_text, user_text = _join_messages_to_text(messages)

    system_text = _clip(system_text, 6000)
    user_text = _clip(user_text, 24000)

    # ---------------- OpenAI ----------------
    if provider == "openai":
        model = model_hint or os.environ.get("OPENAI_MODEL") or "gpt-4.1-mini"
        client = _openai_client()
        resp = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_text or "You are helpful."},
                {"role": "user", "content": user_text},
            ],
        )
        return resp.choices[0].message.content.strip()

    # ---------------- Qwen (OpenAI compatible) ----------------
    if provider == "qwen":
        model = model_hint or os.environ.get("QWEN_MODEL") or "qwen-plus"
        client = _qwen_client()

        # Alibaba docs use /chat/completions endpoint; OpenAI SDK composes it internally
        # from base_url + "/chat/completions" :contentReference[oaicite:3]{index=3}
        resp = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_text or "You are helpful."},
                {"role": "user", "content": user_text},
            ],
        )
        return resp.choices[0].message.content.strip()

    # ---------------- Gemini (google-genai) ----------------
    if provider == "gemini":
        client = _gemini_client()

        # Merge to one prompt string (supported usage) :contentReference[oaicite:4]{index=4}
        prompt = (system_text + "\n\n" + user_text).strip() if system_text else user_text

        # If model_hint given: try it first; else use fallback chain
        fallback_models = []
        if model_hint:
            fallback_models.append(model_hint)

        # Defaults from env, then fallback models known in docs :contentReference[oaicite:5]{index=5}
        env_model = os.environ.get("GEMINI_MODEL_TRANSLATE")
        if env_model:
            fallback_models.append(env_model)

        fallback_models += [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
        ]

        last_err = None
        for model in fallback_models:
            try:
                resp = client.models.generate_content(
                    model=model,
                    contents=prompt,
                )
                text = (resp.text or "").strip()
                if text:
                    return text
                return ""  # rare case
            except genai_errors.ClientError as e:
                # Usually: model not found / not allowed / quota / region restrictions
                last_err = e
                continue

        raise last_err if last_err else RuntimeError("Gemini call failed for unknown reasons.")

    raise ValueError("Nieznany provider LLM. Dozwolone: openai|gemini|qwen")


def review_llm(messages: list, temperature: float = 0.1, model_hint: Optional[str] = None) -> str:
    """
    Review ALWAYS by Gemini, but with fallback models if primary not available.
    Recommended stable choice is often gemini-2.5-flash (availability varies). :contentReference[oaicite:6]{index=6}
    """
    # try explicit review model first, then fallback chain inside chat_llm
    review_model = model_hint or os.environ.get("GEMINI_MODEL_REVIEW") or "gemini-2.5-pro"
    return chat_llm("gemini", messages=messages, temperature=temperature, model_hint=review_model)
