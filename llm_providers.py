import os
from typing import Optional, List, Dict, Tuple

from openai import OpenAI
from google import genai


def _join_messages_to_text(messages: List[Dict[str, str]]) -> Tuple[str, str]:
    """Return (system_text, user_text) from chat-like messages."""
    system_parts = []
    user_parts = []
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
    user_text = "\n\n".join(user_parts).strip()

    if not user_text:
        user_text = " "

    return system_text, user_text


def _clip(text: str, max_chars: int) -> str:
    if not text:
        return text
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 200] + "\n\n[...truncated due to length...]\n"


# -------------------------
# Providers
# -------------------------

def _openai_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Brak OPENAI_API_KEY w secrets/ENV.")
    return OpenAI(api_key=api_key)


def _qwen_client() -> OpenAI:
    """
    Qwen (Alibaba Cloud Model Studio / DashScope) can be called via OpenAI-compatible protocol
    by using OpenAI SDK with a different base_url.
    """
    api_key = os.environ.get("QWEN_API_KEY")
    if not api_key:
        raise RuntimeError("Brak QWEN_API_KEY w secrets/ENV.")

    base_url = os.environ.get("QWEN_BASE_URL") or "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    return OpenAI(api_key=api_key, base_url=base_url)


def _gemini_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Brak GEMINI_API_KEY w secrets/ENV.")
    return genai.Client(api_key=api_key)


def chat_llm(
    provider: str,
    messages: list,
    temperature: float = 0.2,
    model_hint: Optional[str] = None,
) -> str:
    """
    provider: openai | gemini | qwen
    messages: [{"role":"system"|"user", "content":"..."}]
    """
    provider = provider.lower().strip()
    system_text, user_text = _join_messages_to_text(messages)

    # Keep prompts bounded
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
        model = model_hint or os.environ.get("GEMINI_MODEL_TRANSLATE") or "gemini-2.5-flash"
        client = _gemini_client()

        # Gemini SDK uses a single "contents" input; we merge system + user deterministically
        prompt = (system_text + "\n\n" + user_text).strip() if system_text else user_text

        resp = client.models.generate_content(
            model=model,
            contents=prompt,
        )
        return (resp.text or "").strip()

    raise ValueError(f"Nieznany provider LLM: {provider}. Dozwolone: openai|gemini|qwen")


def review_llm(messages: list, temperature: float = 0.1, model_hint: Optional[str] = None) -> str:
    """
    Review ALWAYS by Gemini (as per your requirement).
    """
    model = model_hint or os.environ.get("GEMINI_MODEL_REVIEW") or "gemini-2.5-pro"
    return chat_llm("gemini", messages=messages, temperature=temperature, model_hint=model)
